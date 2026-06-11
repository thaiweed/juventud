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

            # Send email — with fallback if Celery/Redis is not available
            from .tasks import send_order_created_email
            try:
                send_order_created_email.delay(order.id)
            except Exception:
                # Celery unavailable — run synchronously
                try:
                    send_order_created_email(order.id)
                except Exception:
                    pass  # Email failure must not block the order flow

            # Set the order in the session
            request.session['order_id'] = order.id

            payment_url = reverse('payments:process')

            import json
            if is_htmx(request):
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
