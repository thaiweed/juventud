import logging
from datetime import datetime

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import Order

logger = logging.getLogger(__name__)


@shared_task
def send_order_created_email(order_id):
    """
    Sends an HTML confirmation email when an order is placed.
    Falls back to plain text if template rendering fails.
    """
    try:
        order = Order.objects.prefetch_related('items__product').get(id=order_id)
    except Order.DoesNotExist:
        logger.warning("send_order_created_email: Order #%s not found", order_id)
        return False

    subject = f'Order #{order.id} — Juventud'

    try:
        # Build absolute payment URL
        payment_url = f'https://juventudonline.store/payments/process/'

        context = {
            'order': order,
            'payment_url': payment_url,
            'year': datetime.now().year,
        }
        html_body = render_to_string('emails/order_created.html', context)
        text_body = strip_tags(html_body)
    except Exception as e:
        logger.error("Failed to render order_created email template: %s", e)
        # Fallback plain text
        text_body = (
            f"Hi {order.first_name},\n\n"
            f"Your order #{order.id} has been placed successfully.\n"
            f"Please complete your payment at https://juventudonline.store/payments/process/\n\n"
            f"Thank you!"
        )
        html_body = None

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.email],
        )
        if html_body:
            msg.attach_alternative(html_body, 'text/html')
        msg.send()
        logger.info("Order created email sent to %s (order #%s)", order.email, order.id)
        return True
    except Exception as e:
        logger.error("Failed to send order_created email for order #%s: %s", order_id, e)
        return False


@shared_task
def send_payment_success_email(order_id):
    """
    Sends an HTML payment confirmation email after successful payment.
    """
    try:
        order = Order.objects.prefetch_related('items__product').get(id=order_id)
    except Order.DoesNotExist:
        logger.warning("send_payment_success_email: Order #%s not found", order_id)
        return False

    subject = f'Payment Confirmed — Order #{order.id}'

    # Get transaction id from the latest paid payment
    from apps.payments.models import Payment
    payment = Payment.objects.filter(order=order, status='paid').first()
    trans_id = payment.external_id if payment else None

    try:
        context = {
            'order': order,
            'trans_id': trans_id,
            'year': datetime.now().year,
        }
        html_body = render_to_string('emails/payment_success.html', context)
        text_body = strip_tags(html_body)
    except Exception as e:
        logger.error("Failed to render payment_success email template: %s", e)
        text_body = (
            f"Hi {order.first_name},\n\n"
            f"Your payment for order #{order.id} has been confirmed.\n"
            f"Transaction ID: {trans_id or 'N/A'}\n\n"
            f"Thank you for shopping with Juventud!"
        )
        html_body = None

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.email],
        )
        if html_body:
            msg.attach_alternative(html_body, 'text/html')
        msg.send()
        logger.info("Payment success email sent to %s (order #%s)", order.email, order.id)
        return True
    except Exception as e:
        logger.error("Failed to send payment_success email for order #%s: %s", order_id, e)
        return False
