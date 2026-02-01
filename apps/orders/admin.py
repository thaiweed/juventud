from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email',
                    'address', 'postal_code', 'city', 'country', 'paid',
                    'status', 'created', 'updated', 'transaction_id']
    list_filter = ['paid', 'created', 'updated', 'status']
    readonly_fields = ['transaction_id']
    inlines = [OrderItemInline]

    def transaction_id(self, obj):
        if hasattr(obj, 'payment'):
            return obj.payment.transaction_id
        return None
    transaction_id.short_description = 'Transaction ID'
