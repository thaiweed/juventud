from django.db import models
from apps.orders.models import Order


class Payment(models.Model):
    """
    Запись о платеже.

    Модель провайдер-нейтральна — она не содержит полей, специфичных
    для NowPayments или YooKassa. Провайдер-специфичные данные
    хранятся в metadata и raw_response.

    При смене провайдера (например, с NowPayments на YooKassa) —
    схема БД не меняется.
    """

    # ── Нейтральные статусы (не зависят от провайдера) ────────────
    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        PAID      = 'paid',      'Paid'
        FAILED    = 'failed',    'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED  = 'refunded',  'Refunded'

    # ── Поддерживаемые провайдеры ──────────────────────────────────
    class Provider(models.TextChoices):
        NOWPAYMENTS = 'nowpayments', 'NowPayments'
        YOOKASSA    = 'yookassa',    'YooKassa'
        # TODO: добавить новые провайдеры здесь

    # ── Связь с заказом ────────────────────────────────────────────
    # ForeignKey вместо OneToOneField позволяет создавать несколько попыток оплаты
    # для одного заказа (например, первая попытка провалилась, пользователь платит снова)
    order = models.ForeignKey(
        Order,
        related_name='payments',
        on_delete=models.CASCADE,
    )

    # ── Провайдер-нейтральные поля ─────────────────────────────────

    provider = models.CharField(
        max_length=50,
        choices=Provider.choices,
        default=Provider.NOWPAYMENTS,
        verbose_name='Провайдер',
        help_text='Платёжная система, через которую создан платёж',
    )

    external_id = models.CharField(
        max_length=255,
        db_index=True,
        blank=True,
        default='',
        verbose_name='Внешний ID',
        help_text='ID платежа на стороне провайдера',
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Статус',
        db_index=True,
    )

    # Провайдер-специфичный статус (например, "confirming", "sending" у NowPayments)
    provider_status = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='Статус провайдера',
        help_text='Оригинальный статус от платёжной системы',
    )

    currency = models.CharField(
        max_length=10,
        default='RUB',
        verbose_name='Валюта',
        help_text='ISO-код валюты (RUB, USD, EUR, ...)',
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Сумма',
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата оплаты',
        help_text='Когда платёж был подтверждён',
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Метаданные',
        help_text='Провайдер-специфичные данные (адрес крипто-кошелька, и т.д.)',
    )

    raw_response = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Сырой ответ API',
        help_text='Полный ответ от платёжной системы (для дебага)',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Поля обратной совместимости (deprecated) ───────────────────
    # Эти поля оставлены для обратной совместимости с существующими
    # записями в БД. Новый код должен использовать external_id и status.
    # TODO: удалить в следующем мажорном релизе после миграции данных.

    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='[deprecated] Transaction ID',
        help_text='Устаревшее поле. Используйте external_id.',
        db_index=True,
    )

    payment_status = models.CharField(
        max_length=50,
        blank=True,
        default='waiting',
        verbose_name='[deprecated] Payment Status',
        help_text='Устаревшее поле. Используйте status.',
    )

    price_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='[deprecated] Price Amount',
        help_text='Устаревшее поле. Используйте amount.',
    )

    price_currency = models.CharField(
        max_length=10,
        blank=True,
        default='rub',
        verbose_name='[deprecated] Price Currency',
        help_text='Устаревшее поле. Используйте currency.',
    )

    pay_amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name='[deprecated] Pay Amount (NowPayments)',
        help_text='Устаревшее поле. Данные теперь в metadata.',
    )

    pay_currency = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name='[deprecated] Pay Currency (NowPayments)',
        help_text='Устаревшее поле. Данные теперь в metadata.',
    )

    pay_address = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='[deprecated] Pay Address (NowPayments)',
        help_text='Устаревшее поле. Данные теперь в metadata.',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        indexes = [
            models.Index(fields=['external_id']),
            models.Index(fields=['status']),
            models.Index(fields=['order', 'status']),
        ]

    def __str__(self):
        return f'Payment #{self.id} [{self.provider}] {self.status} — Order #{self.order_id}'

    @property
    def is_paid(self) -> bool:
        return self.status == self.Status.PAID

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING
