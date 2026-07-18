"""
Payments Views — только HTTP-слой.

Ответственность views:
    - Получить данные из request
    - Вызвать PaymentService или webhook-обработчик
    - Вернуть HttpResponse

Что views НЕ делают:
    - Не создают объекты Payment напрямую
    - Не знают о NowPayments, YooKassa или любом другом провайдере
    - Не содержат бизнес-логику
"""

import logging

from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.orders.models import Order
from apps.payments.providers.base import PaymentProviderError
from apps.payments.services.payment_service import PaymentService
from apps.payments.utils.registry import get_payment_provider
from apps.payments.webhooks.handlers import handle_payment_webhook

logger = logging.getLogger(__name__)


def _is_htmx(request) -> bool:
    return request.headers.get('HX-Request') == 'true'


# H-2: limit payment initiation — 3 POST per minute per IP.
# Prevents exhausting the payment provider API quota and creating ghost payments.
@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def payment_process(request):
    """
    Инициирует создание платежа.

    GET  → показывает страницу подтверждения заказа
    POST → создаёт платёж через PaymentService, редиректит на провайдера
    """
    order_id = request.session.get('order_id')
    # C-2: verify the current session owns this order (IDOR protection).
    # order_id is a predictable integer — without session_key check an attacker
    # could pay for any order by simply setting order_id in their session.
    order = get_object_or_404(
        Order,
        id=order_id,
        session_key=request.session.session_key,
    )

    if request.method == 'POST':
        provider = get_payment_provider()
        service = PaymentService(provider)

        try:
            redirect_url = service.initiate_payment(order, request)
        except PaymentProviderError as e:
            logger.error("Payment initiation failed for order #%s: %s", order.id, e)
            error_msg = 'Could not create payment. Please try again later.'

            if _is_htmx(request):
                return HttpResponse(
                    f'<p class="text-red-500 text-center py-8">{error_msg}</p>'
                )
            return render(request, 'payments/process.html', {
                'order': order,
                'error': error_msg,
            })
        except Exception as e:
            logger.exception("Unexpected error during payment initiation: %s", e)
            error_msg = 'An unexpected error occurred. Please try again later.'

            if _is_htmx(request):
                return HttpResponse(
                    f'<p class="text-red-500 text-center py-8">{error_msg}</p>'
                )
            return render(request, 'payments/process.html', {
                'order': order,
                'error': error_msg,
            })

        # Редирект на страницу оплаты провайдера
        response = HttpResponse(status=200)
        response['HX-Redirect'] = redirect_url
        return response

    # GET
    context = {'order': order}
    if _is_htmx(request):
        return render(request, 'payments/partials/process_content.html', context)
    return render(request, 'payments/process.html', context)


@csrf_exempt
@require_POST
def payment_webhook(request):
    """
    Обрабатывает входящие webhook-уведомления от активного провайдера.

    Вся логика (верификация, парсинг, обновление БД) вынесена в
    apps/payments/webhooks/handlers.py.

    Endpoint: POST /payments/webhook/
    """
    provider = get_payment_provider()
    success, message = handle_payment_webhook(provider, request)

    if not success:
        logger.warning("Webhook processing failed: %s", message)
        return HttpResponseBadRequest(message)

    return HttpResponse('OK')


# Оставлен для обратной совместимости (старый URL /payments/ipn/)
# TODO: удалить после обновления webhook URL в NowPayments dashboard
@csrf_exempt
@require_POST
def payment_ipn(request):
    """
    [DEPRECATED] Используйте /payments/webhook/ вместо /payments/ipn/.

    Оставлен для обратной совместимости — NowPayments dashboard
    может ещё отправлять на старый URL.
    """
    logger.warning(
        "Deprecated /payments/ipn/ endpoint called. "
        "Please update webhook URL to /payments/webhook/ in NowPayments dashboard."
    )
    return payment_webhook(request)


def payment_success(request):
    return render(request, 'payments/success.html')


def payment_cancel(request):
    return render(request, 'payments/cancel.html')
