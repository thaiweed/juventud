"""
NowPayments Provider Adapter.

Вся логика работы с NowPayments API изолирована здесь.
views.py и PaymentService не знают о существовании этого класса —
они работают только через PaymentProvider (base.py).

Документация: https://nowpayments.io/help/api
"""

import hmac
import hashlib
import json
import logging
from decimal import Decimal

import requests
from django.conf import settings

from .base import PaymentProvider, PaymentProviderError

logger = logging.getLogger(__name__)


class NowPaymentsProvider(PaymentProvider):
    """
    Адаптер для NowPayments API.

    Реализует PaymentProvider. Вся HTTP-логика взаимодействия с NowPayments
    находится только здесь. При переходе на другой провайдер этот файл
    просто перестаёт использоваться — остальной код не меняется.
    """

    API_URL = 'https://api.nowpayments.io/v1'

    # Маппинг NowPayments-статусов на нейтральные статусы Payment.STATUS_*
    STATUS_MAP = {
        'waiting':        'pending',
        'confirming':     'pending',
        'confirmed':      'pending',
        'sending':        'pending',
        'partially_paid': 'pending',
        'finished':       'paid',
        'failed':         'failed',
        'refunded':       'refunded',
        'expired':        'failed',
    }

    def __init__(self):
        self.api_key = settings.NOWPAYMENTS_API_KEY
        self.ipn_secret = settings.NOWPAYMENTS_IPN_SECRET

    # ──────────────────────────────────────────────────────────────
    #  Реализация PaymentProvider
    # ──────────────────────────────────────────────────────────────

    def create_payment(self, order, urls: dict) -> dict:
        """
        Создаёт инвойс через NowPayments Invoice API.

        Возвращает нормализованный словарь с external_id и redirect_url.
        """
        raw = self._create_invoice(
            price_amount=order.get_total_cost(),
            price_currency='rub',
            order_description='Juventud Clothing',
            ipn_callback_url=urls.get('ipn', ''),
            success_url=urls.get('success', ''),
            cancel_url=urls.get('cancel', ''),
        )

        if not raw or 'invoice_url' not in raw:
            raise PaymentProviderError(
                f"NowPayments: failed to create invoice. Response: {raw}"
            )

        return {
            'external_id': str(raw['id']),
            'redirect_url': raw['invoice_url'],
            'raw': raw,
        }

    def get_payment(self, external_id: str) -> dict:
        """
        Получает статус платежа по его ID.

        NowPayments API: GET /v1/payment/{payment_id}
        """
        url = f"{self.API_URL}/payment/{external_id}"
        headers = {'x-api-key': self.api_key}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            raw = response.json()
        except requests.exceptions.RequestException as e:
            logger.error("NowPayments get_payment error: %s", e)
            raise PaymentProviderError(f"NowPayments: get_payment failed: {e}")

        return {
            'external_id': external_id,
            'status': self._map_status(raw.get('payment_status', '')),
            'provider_status': raw.get('payment_status', ''),
            'raw': raw,
        }

    def cancel_payment(self, external_id: str) -> dict:
        """
        NowPayments не поддерживает отмену — документация не предоставляет
        такого endpoint. Возвращаем заглушку.

        TODO: уточнить у NowPayments, есть ли endpoint для отмены.
        """
        logger.warning(
            "NowPayments: cancel_payment called for %s, "
            "but NowPayments does not support cancellation via API.",
            external_id
        )
        return {'external_id': external_id, 'cancelled': False, 'message': 'Not supported'}

    def refund_payment(self, external_id: str, amount: Decimal) -> dict:
        """
        NowPayments поддерживает refund через dashboard, но не через API
        в стандартном плане. Оставляем заглушку.

        TODO: реализовать если NowPayments предоставит API для refund.
        """
        logger.warning(
            "NowPayments: refund_payment called for %s, "
            "refund via API not implemented.",
            external_id
        )
        return {'external_id': external_id, 'refunded': False, 'message': 'Not supported'}

    def verify_webhook(self, request) -> bool:
        """
        Проверяет HMAC-SHA512 подпись NowPayments IPN.

        NowPayments отправляет подпись в заголовке x-nowpayments-sig.
        Подпись вычисляется от JSON-тела с отсортированными ключами.
        """
        x_signature = request.headers.get('x-nowpayments-sig')
        if not x_signature:
            logger.warning("NowPayments IPN: missing x-nowpayments-sig header")
            return False

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            logger.warning("NowPayments IPN: invalid JSON body")
            return False

        return self._check_signature(data, x_signature)

    def parse_webhook(self, request) -> dict:
        """
        Разбирает IPN-запрос от NowPayments и возвращает нормализованные данные.

        NowPayments IPN payload содержит поля:
            payment_id, payment_status, price_amount, price_currency,
            pay_amount, pay_currency, pay_address, order_id, id (invoice_id)
        """
        data = json.loads(request.body)

        provider_status = data.get('payment_status', '')
        neutral_status = self._map_status(provider_status)

        # NowPayments может слать payment_id (ID платежа) или id (ID инвойса)
        # Мы храним invoice ID в external_id, поэтому ищем по нему
        external_id = str(data.get('id') or data.get('payment_id') or '')

        return {
            'external_id': external_id,
            'status': neutral_status,
            'provider_status': provider_status,
            'amount': Decimal(str(data.get('pay_amount', 0))) if data.get('pay_amount') else None,
            'currency': data.get('pay_currency'),
            'metadata': {
                'pay_address': data.get('pay_address'),
                'pay_currency': data.get('pay_currency'),
                'pay_amount': data.get('pay_amount'),
                'payment_id': data.get('payment_id'),
                'invoice_id': data.get('id'),
                'order_id': data.get('order_id'),
            },
            'raw': data,
        }

    # ──────────────────────────────────────────────────────────────
    #  Внутренние методы (NowPayments-специфичная логика)
    # ──────────────────────────────────────────────────────────────

    def _create_invoice(
        self,
        price_amount,
        price_currency,
        order_description,
        ipn_callback_url,
        success_url,
        cancel_url,
        order_id=None,
    ):
        """Вызывает NowPayments Invoice API."""
        url = f"{self.API_URL}/invoice"
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
        }
        payload = {
            "price_amount": float(price_amount),
            "price_currency": price_currency,
            "order_description": order_description,
            "ipn_callback_url": ipn_callback_url,
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        if order_id:
            payload["order_id"] = str(order_id)

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(
                "NowPayments API error on create_invoice: %s | response: %s",
                e,
                getattr(e, 'response', {}).content if hasattr(e, 'response') else '',
            )
            return None

    def _check_signature(self, request_data: dict, received_signature: str) -> bool:
        """
        Верифицирует HMAC-SHA512 подпись от NowPayments.

        Алгоритм: JSON.stringify(sortedKeys(body)) → HMAC-SHA512(ipn_secret)

        Исправлен баг оригинала: hmac.new() → hmac.new() с правильными аргументами.
        """
        sorted_msg = json.dumps(request_data, separators=(',', ':'), sort_keys=True)

        digest = hmac.new(
            key=str(self.ipn_secret).encode('utf-8'),
            msg=sorted_msg.encode('utf-8'),
            digestmod=hashlib.sha512,
        )
        expected_signature = digest.hexdigest()

        # Сравнение через hmac.compare_digest защищает от timing-атак
        return hmac.compare_digest(expected_signature, received_signature)

    def _map_status(self, provider_status: str) -> str:
        """Приводит NowPayments-статус к нейтральному статусу модели Payment."""
        return self.STATUS_MAP.get(provider_status, 'pending')
