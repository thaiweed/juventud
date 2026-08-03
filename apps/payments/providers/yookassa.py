"""
YooKassa Provider — ЗАГЛУШКА (не подключена).

TODO: реализовать после подключения YooKassa.

Для подключения:
    1. pip install yookassa
    2. Добавить в settings.py:
           YOOKASSA_SHOP_ID = config('YOOKASSA_SHOP_ID')
           YOOKASSA_SECRET_KEY = config('YOOKASSA_SECRET_KEY')
    3. Добавить в .env:
           YOOKASSA_SHOP_ID=ваш_shop_id
           YOOKASSA_SECRET_KEY=ваш_secret_key
    4. Реализовать все методы ниже.
    5. В settings.py установить:
           PAYMENT_PROVIDER = "yookassa"

Документация YooKassa API:
    https://yookassa.ru/developers/api
"""

from decimal import Decimal

from .base import PaymentProvider, PaymentProviderError


class YooKassaProvider(PaymentProvider):
    """
    Адаптер для YooKassa API.

    ВНИМАНИЕ: этот класс — заглушка. Все методы бросают NotImplementedError.
    Реализация будет добавлена на следующем этапе.
    """

    def __init__(self):
        # TODO: инициализировать YooKassa SDK
        # from yookassa import Configuration
        # Configuration.account_id = settings.YOOKASSA_SHOP_ID
        # Configuration.secret_key = settings.YOOKASSA_SECRET_KEY
        pass

    def create_payment(self, order, urls: dict) -> dict:
        """
        TODO: создать платёж через YooKassa.

        YooKassa использует:
            - idempotency_key (str) — для идемпотентности
            - confirmation.type = 'redirect'
            - confirmation.return_url

        Пример:
            from yookassa import Payment as YKPayment
            payment = YKPayment.create({
                "amount": {"value": str(order.get_total_with_shipping()), "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": urls['success']},
                "capture": True,
                "description": f"Order #{order.id}",
            }, idempotency_key)
        """
        raise NotImplementedError(
            "YooKassaProvider.create_payment() is not implemented yet. "
            "See apps/payments/providers/yookassa.py for TODO instructions."
        )

    def get_payment(self, external_id: str) -> dict:
        """
        TODO: получить статус платежа через YooKassa.

        from yookassa import Payment as YKPayment
        payment = YKPayment.find_one(external_id)
        """
        raise NotImplementedError("YooKassaProvider.get_payment() is not implemented yet.")

    def cancel_payment(self, external_id: str) -> dict:
        """
        TODO: отменить платёж через YooKassa.

        from yookassa import Payment as YKPayment
        payment = YKPayment.cancel(external_id, idempotency_key)
        """
        raise NotImplementedError("YooKassaProvider.cancel_payment() is not implemented yet.")

    def refund_payment(self, external_id: str, amount: Decimal) -> dict:
        """
        TODO: создать возврат через YooKassa Refund API.

        from yookassa import Refund
        refund = Refund.create({
            "payment_id": external_id,
            "amount": {"value": str(amount), "currency": "RUB"},
        }, idempotency_key)
        """
        raise NotImplementedError("YooKassaProvider.refund_payment() is not implemented yet.")

    def verify_webhook(self, request) -> bool:
        """
        TODO: верифицировать входящий webhook от YooKassa.

        YooKassa отправляет уведомления на webhook-URL.
        Верификация: сравнить IP отправителя со списком разрешённых IP YooKassa.
        Или использовать Basic Auth.

        Список IP YooKassa:
            185.71.76.0/27, 185.71.77.0/27, 77.75.153.0/25,
            77.75.156.11, 77.75.156.35, 77.75.154.128/25, 2a02:5180::/32

        Документация:
            https://yookassa.ru/developers/using-api/webhooks
        """
        raise NotImplementedError("YooKassaProvider.verify_webhook() is not implemented yet.")

    def parse_webhook(self, request) -> dict:
        """
        TODO: разобрать webhook-уведомление от YooKassa.

        YooKassa отправляет JSON с полями:
            type: "notification"
            event: "payment.succeeded" | "payment.canceled" | "refund.succeeded"
            object: { id, status, amount, ... }

        STATUS_MAP для YooKassa:
            "pending"   → "pending"
            "waiting_for_capture" → "pending"
            "succeeded" → "paid"
            "canceled"  → "cancelled"
        """
        raise NotImplementedError("YooKassaProvider.parse_webhook() is not implemented yet.")
