"""
PaymentService — слой бизнес-логики платёжной подсистемы.

Ответственность:
    - Инициировать создание платежа через провайдер
    - Сохранить Payment в БД
    - Вернуть URL для редиректа пользователя

PaymentService знает только о PaymentProvider (абстракция).
Он не знает о NowPayments, YooKassa или любом другом провайдере.
views.py не знает о провайдере — только о PaymentService.
"""

import logging

from apps.payments.models import Payment
from apps.payments.providers.base import PaymentProvider, PaymentProviderError

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Управляет жизненным циклом платежей.

    Usage:
        from apps.payments.utils.registry import get_payment_provider
        from apps.payments.services.payment_service import PaymentService

        provider = get_payment_provider()
        service = PaymentService(provider)
        redirect_url = service.initiate_payment(order, request)
    """

    def __init__(self, provider: PaymentProvider):
        self.provider = provider

    def initiate_payment(self, order, request) -> str:
        """
        Создаёт платёж через провайдер и сохраняет Payment в БД.

        Args:
            order: объект Order
            request: Django HttpRequest (для построения абсолютных URL)

        Returns:
            URL для редиректа пользователя на страницу оплаты

        Raises:
            PaymentProviderError: если провайдер не смог создать платёж
        """
        urls = self._build_callback_urls(request)

        # Создаём платёж через провайдер
        payment_data = self.provider.create_payment(order, urls)

        # Определяем имя провайдера для записи в БД
        provider_name = self._get_provider_name()

        # Сохраняем Payment (или обновляем существующий pending-платёж)
        self._save_payment(order, payment_data, provider_name)

        return payment_data['redirect_url']

    # ──────────────────────────────────────────────────────────────
    #  Вспомогательные методы
    # ──────────────────────────────────────────────────────────────

    def _build_callback_urls(self, request) -> dict:
        """Строит абсолютные URL для callback/redirect."""
        domain = request.build_absolute_uri('/')[:-1]
        return {
            'ipn':     f"{domain}/payments/webhook/",
            'success': f"{domain}/payments/success/",
            'cancel':  f"{domain}/payments/cancel/",
        }

    def _save_payment(self, order, payment_data: dict, provider_name: str) -> Payment:
        """
        Создаёт или обновляет запись Payment в БД.

        Если у заказа уже есть незавершённый платёж — обновляем его
        вместо создания нового (поддержка повторных попыток оплаты).
        """
        external_id = payment_data['external_id']
        amount = order.get_total_cost()

        # Ищем существующий незавершённый платёж для этого заказа
        existing = Payment.objects.filter(
            order=order,
            status='pending',
        ).last()

        if existing:
            existing.external_id = external_id
            existing.provider = provider_name
            existing.amount = amount
            existing.raw_response = payment_data.get('raw', {})
            existing.save(update_fields=[
                'external_id', 'provider', 'amount', 'raw_response', 'updated_at'
            ])
            logger.info(
                "Updated existing pending Payment #%s for Order #%s. "
                "New external_id: %s",
                existing.id, order.id, external_id,
            )
            return existing

        # Создаём новый платёж
        payment = Payment.objects.create(
            order=order,
            provider=provider_name,
            external_id=external_id,
            status='pending',
            amount=amount,
            currency='RUB',
            raw_response=payment_data.get('raw', {}),
            # Обратная совместимость со старыми полями
            transaction_id=external_id,
            price_amount=amount,
            price_currency='rub',
            payment_status='waiting',
        )

        logger.info(
            "Created Payment #%s for Order #%s via %s. external_id: %s",
            payment.id, order.id, provider_name, external_id,
        )
        return payment

    def _get_provider_name(self) -> str:
        """Возвращает строковое имя текущего провайдера."""
        from django.conf import settings
        return getattr(settings, 'PAYMENT_PROVIDER', 'nowpayments')
