from django.db import models
from apps.orders.models import Order

class Payment(models.Model):
    STATUS_Choices = (
        ('waiting', 'Waiting'),
        ('confirming', 'Confirming'),
        ('confirmed', 'Confirmed'),
        ('sending', 'Sending'),
        ('partially_paid', 'Partially Paid'),
        ('finished', 'Finished'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('expired', 'Expired'),
    )

    order = models.OneToOneField(Order, related_name='payment', on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100, unique=True)
    payment_status = models.CharField(max_length=20, choices=STATUS_Choices, default='waiting')
    price_amount = models.DecimalField(max_digits=10, decimal_places=2)
    price_currency = models.CharField(max_length=10, default='usd')
    pay_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    pay_currency = models.CharField(max_length=10, null=True, blank=True)
    pay_address = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Payment {self.payment_id} for Order {self.order.id}'
