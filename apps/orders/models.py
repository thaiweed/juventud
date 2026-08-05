import uuid
from django.db import models
from apps.catalog.models import Product

class Order(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    address = models.CharField(max_length=250)
    postal_code = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default='created', choices=(
        ('created', 'Created'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('cancelled', 'Cancelled'),
    ))
    paid = models.BooleanField(default=False)
    cdek_tracking_number = models.CharField(
        max_length=100, 
        blank=True, 
        default='',
        verbose_name='CDEK Tracking Number',
        help_text='If set and status changes to Shipped, an email will be sent to the customer.'
    )

    # C-2: session ownership — used to verify the requester owns this order
    # Prevents IDOR: attacker cannot pay for someone else's order by guessing order_id
    session_key = models.CharField(
        max_length=40,
        blank=True,
        default='',
        db_index=True,
        help_text='Django session key at order creation time',
    )

    # L-1: non-enumerable public identifier (UUID)
    # Prevents order count disclosure via sequential integer IDs
    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text='Public-facing UUID — safe to expose in URLs/emails',
    )
    
    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['-created']),
        ]

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        if not is_new:
            try:
                old_order = Order.objects.get(pk=self.pk)
                old_status = old_order.status
            except Order.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)

        if not is_new and old_status:
            if self.status == 'shipped' and old_status != 'shipped' and self.cdek_tracking_number:
                from apps.orders.tasks import send_shipped_email
                send_shipped_email.delay(self.id)

    def __str__(self):
        return f'Order {self.id}'

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

    def get_total_with_shipping(self):
        from django.conf import settings
        return self.get_total_cost() + settings.SHIPPING_COST


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    color = models.CharField(max_length=50, blank=True, default='', verbose_name='Цвет')
    size = models.CharField(max_length=20, blank=True, default='', verbose_name='Размер')

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity
