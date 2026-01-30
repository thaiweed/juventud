from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from apps.orders.models import Order
from .models import Payment
from .services import NowPaymentsService
import json

def payment_process(request):
    order_id = request.session.get('order_id')
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        # Initiate payment
        service = NowPaymentsService()
        
        # Define callback URLs
        # In production these should be absolute URLs from sites domain
        # identifying the order or payment? NOWPayments keeps metadata?
        # order_id param in create_invoice is useful.
        
        domain = request.build_absolute_uri('/')[:-1] # Get base domain http://yoursite.com
        ipn_url = f"{domain}/payments/ipn/"
        success_url = f"{domain}/payments/success/"
        cancel_url = f"{domain}/payments/cancel/"
        
        # Create invoice
        # Price from order.get_total_cost()
        price_amount = order.get_total_cost()
        
        invoice_data = service.create_invoice(
            order_id=order.id,
            price_amount=price_amount,
            price_currency='usd', # Defaulting to USD as per model default
            order_description=f'Order {order.id}',
            ipn_callback_url=ipn_url,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        if invoice_data and 'invoice_url' in invoice_data:
            # Create Payment record
            Payment.objects.create(
                order=order,
                payment_id=invoice_data['id'],
                payment_status='waiting',
                price_amount=price_amount,
                price_currency='usd'
            )
            
            # Redirect user to NOWPayments
            return redirect(invoice_data['invoice_url'])
        else:
            # Handle error
            return render(request, 'payments/error.html', {'error': 'Could not create payment invoice'})
            
    return render(request, 'payments/process.html', {'order': order})


@csrf_exempt
@require_POST
def payment_ipn(request):
    service = NowPaymentsService()
    
    # Check signature
    x_signature = request.headers.get('x-nowpayments-sig')
    if not x_signature:
        return HttpResponseBadRequest('No signature provided')
        
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest('Invalid JSON')
        
    if not service.check_signature(data, x_signature):
        return HttpResponseBadRequest('Invalid signature')
        
    # Process status update
    # Data contains: payment_status, payment_id, order_id, etc.
    payment_id = data.get('payment_id') # This might be invoice ID or payment ID depending on flow
    # In 'create_invoice', we get 'id' which is invoice ID.
    # IPN sends 'payment_id' if a payment is made on that invoice?
    # Or 'parent_payment_id'?
    # Let's verify data structure from documentation or assume standard fields.
    # Doc says: "The body of the request is similiar to a get payment status response body."
    
    status = data.get('payment_status')
    order_id = data.get('order_id')
    
    if order_id:
        try:
            order = Order.objects.get(id=order_id)
            payment = Payment.objects.get(order=order)
            
            payment.payment_status = status
            payment.pay_amount = data.get('pay_amount')
            payment.pay_currency = data.get('pay_currency')
            payment.pay_address = data.get('pay_address')
            payment.save()
            
            if status == 'finished' or status == 'confirmed':
                order.paid = True
                order.save()
                
        except (Order.DoesNotExist, Payment.DoesNotExist):
            pass # Log error
            
    return HttpResponse('OK')


def payment_success(request):
    return render(request, 'payments/success.html')

def payment_cancel(request):
    return render(request, 'payments/cancel.html')
