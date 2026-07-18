from abc import ABC, abstractmethod
from decimal import Decimal


class PaymentProvider(ABC):
    """
    Абстрактный контракт для любого платёжного провайдера.

    Каждый новый провайдер (YooKassa, Stripe, etc.) должен реализовать
    все методы этого класса. views.py и PaymentService работают только
    с этим интерфейсом — они не знают, какой провайдер используется.
    """

    @abstractmethod
    def create_payment(self, order, urls: dict) -> dict:
        """
        Создаёт платёж / инвойс на стороне провайдера.

        Args:
            order: объект Order
            urls: словарь с callback URL-адресами:
                  {
                      'ipn': str,       # webhook / IPN URL
                      'success': str,   # редирект после успешной оплаты
                      'cancel': str,    # редирект после отмены
                  }

        Returns:
            Словарь с как минимум:
            {
                'external_id': str,    # ID платежа у провайдера
                'redirect_url': str,   # URL для редиректа пользователя
                'raw': dict,           # сырой ответ API провайдера
            }

        Raises:
            PaymentProviderError: при ошибке создания платежа
        """
        ...

    @abstractmethod
    def get_payment(self, external_id: str) -> dict:
        """
        Получает текущий статус платежа у провайдера по его внешнему ID.

        Returns:
            Словарь с полями: external_id, status, raw
        """
        ...

    @abstractmethod
    def cancel_payment(self, external_id: str) -> dict:
        """
        Отменяет платёж у провайдера.

        Returns:
            Словарь с результатом операции
        """
        ...

    @abstractmethod
    def refund_payment(self, external_id: str, amount: Decimal) -> dict:
        """
        Создаёт возврат платежа.

        Args:
            external_id: ID платежа у провайдера
            amount: сумма возврата

        Returns:
            Словарь с результатом операции
        """
        ...

    @abstractmethod
    def verify_webhook(self, request) -> bool:
        """
        Проверяет подпись/аутентичность входящего webhook-запроса.

        Args:
            request: Django HttpRequest

        Returns:
            True если запрос валиден, False — если нет
        """
        ...

    @abstractmethod
    def parse_webhook(self, request) -> dict:
        """
        Разбирает тело webhook-запроса и возвращает нормализованные данные.

        Каждый провайдер имеет свой формат webhook. Этот метод приводит
        данные к единому виду, понятному PaymentService.

        Returns:
            Нормализованный словарь:
            {
                'external_id': str,          # ID платежа у провайдера
                'status': str,               # нейтральный статус (см. Payment.STATUS_*)
                'provider_status': str,      # оригинальный статус от провайдера
                'amount': Decimal | None,
                'currency': str | None,
                'metadata': dict,            # любые доп. данные провайдера
            }
        """
        ...


class PaymentProviderError(Exception):
    """Базовое исключение для ошибок платёжного провайдера."""
    pass
