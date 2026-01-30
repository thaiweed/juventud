from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'order', 'payment_status', 'price_amount', 'created_at']
    list_filter = ['payment_status', 'created_at']
