from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    fields = ['product', 'price', 'quantity', 'color', 'size']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email',
                    'address', 'postal_code', 'city', 'country', 'paid',
                    'status', 'created', 'updated', 'transaction_id', 'delete_button']
    list_filter = ['paid', 'created', 'updated', 'status']
    readonly_fields = ['transaction_id']
    inlines = [OrderItemInline]

    def transaction_id(self, obj):
        if hasattr(obj, 'payment'):
            return obj.payment.transaction_id
        return None
    transaction_id.short_description = 'Transaction ID'

    def delete_button(self, obj):
        url = reverse('admin:orders_order_delete', args=[obj.pk])
        return format_html('<a class="button" style="color: white; background-color: #ba2121; padding: 4px 8px; border-radius: 4px; text-decoration: none;" href="{}">Удалить</a>', url)
    delete_button.short_description = 'Действие'
