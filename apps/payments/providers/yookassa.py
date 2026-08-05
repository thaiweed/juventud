import json
import logging
import uuid
from decimal import Decimal

import requests
from django.conf import settings

from .base import PaymentProvider, PaymentProviderError

logger = logging.getLogger(__name__)


class YooKassaProvider(PaymentProvider):
    """
    Адаптер для YooKassa API (через requests).
    Документация: https://yookassa.ru/developers/api
    """

    BASE_URL = "https://api.yookassa.ru/v3"

    def __init__(self):
        self.shop_id = getattr(settings, 'YOOKASSA_SHOP_ID', '')
        self.secret_key = getattr(settings, 'YOOKASSA_SECRET_KEY', '')
        if not self.shop_id or not self.secret_key:
            logger.warning("YooKassa credentials are not set in settings.py")

    def _get_auth(self):
        return (self.shop_id, self.secret_key)

    def create_payment(self, order, urls: dict) -> dict:
        """
        Создаёт платёж в YooKassa и возвращает redirect_url.
        """
        url = f"{self.BASE_URL}/payments"
        idempotence_key = str(uuid.uuid4())
        
        payload = {
            "amount": {
                "value": str(order.get_total_with_shipping()),
                "currency": "RUB"
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": urls.get('success', '')
            },
            "description": f"Заказ #{order.id} на Juventud",
            "metadata": {
                "order_id": order.id
            }
        }

        headers = {
            "Idempotence-Key": idempotence_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                auth=self._get_auth(), 
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # В зависимости от метода оплаты, YooKassa возвращает confirmation_url
            redirect_url = data.get('confirmation', {}).get('confirmation_url')
            if not redirect_url:
                raise PaymentProviderError(f"YooKassa response missing confirmation_url: {data}")
                
            return {
                "external_id": data.get("id"),
                "status": "pending",
                "redirect_url": redirect_url,
                "amount": payload["amount"]["value"],
                "currency": "RUB",
                "raw_response": data
            }
        except requests.RequestException as e:
            logger.error("YooKassa API Error (create_payment): %s", e)
            raise PaymentProviderError(f"Failed to create YooKassa payment: {e}")

    def get_payment(self, external_id: str) -> dict:
        """
        Получает актуальный статус платежа из API YooKassa.
        Используется для сверки при обработке вебхуков.
        """
        url = f"{self.BASE_URL}/payments/{external_id}"
        try:
            response = requests.get(
                url, 
                auth=self._get_auth(), 
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error("YooKassa API Error (get_payment): %s", e)
            raise PaymentProviderError(f"Failed to get YooKassa payment: {e}")

    def cancel_payment(self, external_id: str) -> dict:
        raise NotImplementedError("Cancel is not used in the current flow for YooKassa.")

    def refund_payment(self, external_id: str, amount: Decimal) -> dict:
        raise NotImplementedError("Refund is not implemented yet.")

    def verify_webhook(self, request) -> bool:
        """
        Верификация вебхука. 
        Чтобы не мучиться с проверкой IP-адресов, мы просто возвращаем True,
        а в parse_webhook делаем дополнительный запрос get_payment(external_id) 
        к API YooKassa, чтобы гарантированно узнать статус от самого сервера ЮKassa.
        """
        return True

    def parse_webhook(self, request) -> dict:
        """
        Разбирает вебхук YooKassa.
        """
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            raise PaymentProviderError("Invalid JSON in YooKassa webhook")

        event = data.get('event')
        obj = data.get('object', {})
        external_id = obj.get('id')

        if not external_id:
            raise PaymentProviderError("Missing payment id in YooKassa webhook")

        # Дополнительная проверка статуса напрямую в ЮKassa для безопасности
        actual_payment = self.get_payment(external_id)
        
        status = actual_payment.get('status')
        order_id = actual_payment.get('metadata', {}).get('order_id')
        
        # Маппинг статусов
        status_map = {
            "pending": "pending",
            "waiting_for_capture": "pending",
            "succeeded": "paid",
            "canceled": "cancelled"
        }
        
        mapped_status = status_map.get(status, "failed")

        return {
            "external_id": external_id,
            "status": mapped_status,
            "order_id": order_id,
            "amount": actual_payment.get('amount', {}).get('value'),
            "currency": actual_payment.get('amount', {}).get('currency'),
            "raw_payload": actual_payment
        }
