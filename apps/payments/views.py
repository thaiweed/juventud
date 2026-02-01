from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from apps.orders.models import Order
from .models import Payment
from .services import NowPaymentsService
import json

def is_htmx(request):
    return request.headers.get('HX-Request') == 'true'

def payment_process(request):
    order_id = request.session.get('order_id')
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        # Initiate payment
        service = NowPaymentsService()
        
        domain = request.build_absolute_uri('/')[:-1] # Get base domain http://yoursite.com
        ipn_url = f"{domain}/payments/ipn/"
        success_url = f"{domain}/payments/success/"
        cancel_url = f"{domain}/payments/cancel/"
        
        # Create invoice
        price_amount = order.get_total_cost()
        
        invoice_data = service.create_invoice(
            order_id=None,
            price_amount=price_amount,
            price_currency='rub', 
            order_description='Juventud Clothing',
            ipn_callback_url=ipn_url,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        if invoice_data and 'invoice_url' in invoice_data:
            # Create Payment record
            Payment.objects.create(
                order=order,
                transaction_id=invoice_data['id'],
                payment_status='waiting',
                price_amount=price_amount,
                price_currency='rub'
            )
            
            # Redirect user to NOWPayments
            # Since this is triggered via HTMX from process.html, we need HX-Redirect
            # to force the browser to navigate to the external URL.
            response = HttpResponse(status=200)
            response['HX-Redirect'] = invoice_data['invoice_url']
            return response
        else:
            # Handle error
            # If HTMX, return error partial?
            error_msg = 'Could not create payment invoice'
            if is_htmx(request):
                 return HttpResponse(f'<div class="text-red-500">{error_msg}</div>')
            return render(request, 'payments/error.html', {'error': error_msg})
            
    # GET Request
    context = {'order': order}
    if is_htmx(request):
        return render(request, 'payments/partials/process_content.html', context)

    return render(request, 'payments/process.html', context)


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
    invoice_id = data.get('id')
    
    payment = None
    order = None

    try:
        if invoice_id:
            payment = Payment.objects.filter(transaction_id=invoice_id).last()
        
        if not payment and order_id:
            order = Order.objects.get(id=order_id)
            payment = Payment.objects.get(order=order)
            
        if payment:
            order = payment.order
            
            payment.payment_status = status
            payment.pay_amount = data.get('pay_amount')
            payment.pay_currency = data.get('pay_currency')
            payment.pay_address = data.get('pay_address')
            payment.save()
            
            if status == 'finished' or status == 'confirmed':
                order.paid = True
                order.save()
                # Send success email
                from apps.orders.tasks import send_payment_success_email
                send_payment_success_email.delay(order.id)
                
    except (Order.DoesNotExist, Payment.DoesNotExist):
        pass # Log error
            
    return HttpResponse('OK')


def payment_success(request):
    return render(request, 'payments/success.html')

def payment_cancel(request):
    return render(request, 'payments/cancel.html')
