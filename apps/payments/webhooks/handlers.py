"""
Идемпотентный обработчик входящих webhook-уведомлений.

Ответственность:
    - Верифицировать подпись запроса через провайдер
    - Разобрать данные через провайдер
    - Идемпотентно обновить Payment (защита от дублей)
    - Обновить Order.paid при успешной оплате
    - Запустить Celery-задачу отправки email

Идемпотентность обеспечивается через:
    - SELECT FOR UPDATE при чтении Payment
    - Проверку, что статус уже не является финальным перед обновлением
"""

import logging

from django.db import transaction

from apps.payments.providers.base import PaymentProvider

logger = logging.getLogger(__name__)

# Финальные статусы — после их установки webhook больше не должен менять статус
FINAL_STATUSES = {'paid', 'failed', 'cancelled', 'refunded'}


def handle_payment_webhook(provider: PaymentProvider, request) -> tuple[bool, str]:
    """
    Идемпотентно обрабатывает входящий webhook-запрос.

    Args:
        provider: активный PaymentProvider
        request: Django HttpRequest

    Returns:
        (success: bool, message: str)

    Flow:
        1. Верифицировать подпись
        2. Разобрать тело запроса
        3. Найти Payment по external_id (SELECT FOR UPDATE)
        4. Проверить идемпотентность (статус уже финальный?)
        5. Обновить Payment.status
        6. Если paid → обновить Order.paid = True + задача Celery
    """
    # 1. Верификация подписи
    if not provider.verify_webhook(request):
        logger.warning(
            "Webhook verification failed. Provider: %s | IP: %s",
            provider.__class__.__name__,
            request.META.get('REMOTE_ADDR'),
        )
        return False, "Invalid signature"

    # 2. Парсинг данных
    try:
        webhook_data = provider.parse_webhook(request)
    except Exception as e:
        logger.exception("Failed to parse webhook body: %s", e)
        return False, "Parse error"

    external_id = webhook_data.get('external_id')
    new_status = webhook_data.get('status', 'pending')

    if not external_id:
        logger.warning("Webhook received with no external_id. Data: %s", webhook_data)
        return False, "No external_id"

    # 3–6. Атомарное идемпотентное обновление
    try:
        _update_payment_atomic(external_id, new_status, webhook_data)
    except Exception as e:
        logger.exception(
            "Error processing webhook for external_id=%s: %s", external_id, e
        )
        return False, "Internal error"

    return True, "OK"


@transaction.atomic
def _update_payment_atomic(external_id: str, new_status: str, webhook_data: dict):
    """
    Атомарно обновляет Payment и связанный Order.

    SELECT FOR UPDATE блокирует строку на время транзакции,
    предотвращая гонку при параллельных webhook-запросах.
    """
    from apps.payments.models import Payment

    try:
        payment = (
            Payment.objects
            .select_for_update()
            .select_related('order')
            .get(external_id=external_id)
        )
    except Payment.DoesNotExist:
        logger.warning(
            "Webhook received for unknown external_id: %s", external_id
        )
        return

    # Идемпотентность: если статус уже финальный — ничего не делаем
    if payment.status in FINAL_STATUSES:
        logger.info(
            "Webhook ignored: Payment %s already in final status '%s'. "
            "Incoming status: '%s'.",
            external_id, payment.status, new_status,
        )
        return

    # Обновляем поля Payment
    old_status = payment.status
    payment.status = new_status
    payment.provider_status = webhook_data.get('provider_status', '')

    if webhook_data.get('amount'):
        payment.amount = webhook_data['amount']
    if webhook_data.get('currency'):
        payment.currency = webhook_data['currency']

    # Сохраняем сырой ответ и metadata для дебага
    payment.raw_response = webhook_data.get('raw', {})

    # Мёрджим metadata (не заменяем, а дополняем)
    existing_meta = payment.metadata or {}
    existing_meta.update(webhook_data.get('metadata', {}))
    payment.metadata = existing_meta

    # Если оплачен — фиксируем время и помечаем заказ
    if new_status == 'paid' and old_status != 'paid':
        from django.utils import timezone
        payment.paid_at = timezone.now()
        payment.save()

        order = payment.order
        order.paid = True
        order.save(update_fields=['paid', 'updated'])

        logger.info(
            "Payment %s marked as PAID. Order #%s is now paid.",
            external_id, order.id,
        )

        # Запускаем Celery-задачу отправки email об успешной оплате
        _trigger_payment_success_email(order.id)
    else:
        payment.save()
        logger.info(
            "Payment %s status updated: %s → %s",
            external_id, old_status, new_status,
        )


def _trigger_payment_success_email(order_id: int):
    """Запускает Celery-задачу отправки email об успешной оплате."""
    try:
        from apps.orders.tasks import send_payment_success_email
        send_payment_success_email.delay(order_id)
        logger.info("Scheduled payment success email for order #%s", order_id)
    except Exception as e:
        # Email — не критичная операция, не должна ронять обработку webhook
        logger.error(
            "Failed to schedule payment success email for order #%s: %s",
            order_id, e,
        )
