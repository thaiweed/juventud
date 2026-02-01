from django.shortcuts import render, redirect, HttpResponse
from django.urls import reverse
from .models import OrderItem
from .forms import OrderCreateForm
from apps.cart.cart import Cart

def is_htmx(request):
    return request.headers.get('HX-Request') == 'true'

def order_create(request):
    cart = Cart(request)
    if len(cart) == 0:
        if is_htmx(request):
            response = redirect('catalog:product_list')
            response['HX-Redirect'] = reverse('catalog:product_list')
            return response
        return redirect('catalog:product_list')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save()
            for item in cart:
                OrderItem.objects.create(order=order,
                                         product=item['product'],
                                         price=item['price'],
                                         quantity=item['quantity'])
            
            # Clear the cart
            cart.clear()
            
            # Launch asynchronous task
            from .tasks import send_order_created_email
            send_order_created_email.delay(order.id)
            
            # Set the order in the session
            request.session['order_id'] = order.id
            
            # Redirect to payment process
            # For HTMX, we need to handle the redirect to the payment processing view
            # The payment processing view will eventually redirect to external NOWPayments
            
            payment_url = reverse('payments:process')
            
            import json
            if is_htmx(request):
                # Use HX-Location to trigger a client-side HTMX request to the new URL
                # This maintains SPA behavior (no full reload)
                response = HttpResponse(status=204)
                response['HX-Location'] = json.dumps({
                    'path': payment_url,
                    'target': '#main-content',
                    'swap': 'innerHTML'
                })
                return response
                
            return redirect('payments:process')
    else:
        form = OrderCreateForm()
    
    context = {'cart': cart, 'form': form, 'is_htmx': is_htmx(request)}
    
    if is_htmx(request):
        return render(request, 'orders/order/partials/create_content.html', context)
    
    return render(request, 'orders/order/create.html', context)
