"""
Dependency Injection реестр платёжных провайдеров.

Выбор провайдера определяется настройкой PAYMENT_PROVIDER в settings.py:

    PAYMENT_PROVIDER = "nowpayments"   # или "yookassa"

Все views.py и PaymentService получают провайдер только через get_payment_provider().
Это единственное место в проекте, где происходит привязка к конкретному провайдеру.
"""

import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from apps.payments.providers.base import PaymentProvider

logger = logging.getLogger(__name__)

# Реестр: имя → путь к классу провайдера
_PROVIDER_REGISTRY: dict[str, str] = {
    'nowpayments': 'apps.payments.providers.nowpayments.NowPaymentsProvider',
    'yookassa':    'apps.payments.providers.yookassa.YooKassaProvider',
    # TODO: добавить новые провайдеры здесь:
    # 'stripe': 'apps.payments.providers.stripe.StripeProvider',
}


def get_payment_provider() -> PaymentProvider:
    """
    Возвращает экземпляр активного платёжного провайдера.

    Провайдер определяется через settings.PAYMENT_PROVIDER.
    Провайдер инстанциируется при каждом вызове (stateless).

    Usage:
        from apps.payments.utils.registry import get_payment_provider

        provider = get_payment_provider()
        result = provider.create_payment(order, urls)
    """
    provider_name = getattr(settings, 'PAYMENT_PROVIDER', 'nowpayments')

    class_path = _PROVIDER_REGISTRY.get(provider_name)
    if not class_path:
        raise ImproperlyConfigured(
            f"Unknown PAYMENT_PROVIDER: '{provider_name}'. "
            f"Available providers: {list(_PROVIDER_REGISTRY.keys())}"
        )

    provider_class = _import_class(class_path)

    logger.debug("PaymentProvider resolved: %s", class_path)
    return provider_class()


def _import_class(dotted_path: str):
    """Динамически импортирует класс по dotted-path строке."""
    module_path, class_name = dotted_path.rsplit('.', 1)

    try:
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImproperlyConfigured(
            f"Could not import payment provider class '{dotted_path}': {e}"
        )
