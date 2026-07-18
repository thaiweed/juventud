from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('process/', views.payment_process, name='process'),
    path('webhook/', views.payment_webhook, name='webhook'),
    path('ipn/', views.payment_ipn, name='ipn'),  # deprecated, backward compat
    path('success/', views.payment_success, name='success'),
    path('cancel/', views.payment_cancel, name='cancel'),
]
