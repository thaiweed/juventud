from celery import shared_task
from django.core.mail import send_mail
from .models import Order
from apps.payments.models import Payment

from django.conf import settings

@shared_task
def send_order_created_email(order_id):
    """
    Task to send an e-mail notification when an order is successfully created.
    """
    try:
        order = Order.objects.get(id=order_id)
        subject = f'Order nr. {order.id}'
        message = f'Dear {order.first_name},\n\nYou have successfully placed an order.\nYour order ID is {order.id}.\n\nPlease proceed to payment to complete your purchase.'
        mail_sent = send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.email])
        return mail_sent
    except Order.DoesNotExist:
        return False

@shared_task
def send_payment_success_email(order_id):
    """
    Task to send an e-mail notification when payment is successful.
    """
    try:
        order = Order.objects.get(id=order_id)
        # Try to get payment info if available
        payment = Payment.objects.filter(order=order, payment_status='finished').first()
        trans_id = payment.transaction_id if payment else 'N/A'
        
        subject = f'Payment Confirmed - Order nr. {order.id}'
        message = f'Dear {order.first_name},\n\nYour payment for Order {order.id} has been successfully received.\nTransaction ID: {trans_id}\n\nThank you for shopping with us!'
        
        mail_sent = send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.email])
        return mail_sent
    except Order.DoesNotExist:
        return False
