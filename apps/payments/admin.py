from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'order', 'provider', 'status', 'amount', 'currency',
        'external_id', 'paid_at', 'created_at',
    ]
    list_filter = ['status', 'provider', 'currency', 'created_at']
    search_fields = ['external_id', 'transaction_id', 'order__id']
    readonly_fields = [
        'external_id', 'provider', 'status', 'provider_status',
        'amount', 'currency', 'paid_at',
        'metadata', 'raw_response', 'created_at', 'updated_at',
        # deprecated fields (read-only, не редактируем)
        'transaction_id', 'payment_status', 'price_amount', 'price_currency',
        'pay_amount', 'pay_currency', 'pay_address',
    ]
    fieldsets = (
        ('Основное', {
            'fields': ('order', 'provider', 'external_id', 'status', 'provider_status'),
        }),
        ('Финансы', {
            'fields': ('amount', 'currency', 'paid_at'),
        }),
        ('Данные провайдера', {
            'fields': ('metadata', 'raw_response'),
            'classes': ('collapse',),
        }),
        ('Устаревшие поля (deprecated)', {
            'fields': (
                'transaction_id', 'payment_status', 'price_amount', 'price_currency',
                'pay_amount', 'pay_currency', 'pay_address',
            ),
            'classes': ('collapse',),
            'description': (
                'Эти поля устарели. Они оставлены для обратной совместимости '
                'с существующими записями. Новые записи используют поля выше.'
            ),
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
