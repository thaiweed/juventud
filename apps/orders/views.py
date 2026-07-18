from django.shortcuts import render, redirect, HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit
from .models import OrderItem
from .forms import OrderCreateForm
from apps.cart.cart import Cart

def is_htmx(request):
    return request.headers.get('HX-Request') == 'true'

# H-2: limit order creation — 5 POST attempts per minute per IP.
# Prevents mass order spam that would flood the DB and consume MailerSend quota.
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
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
                # Always fetch current price from the DB at order creation time.
                # This prevents price manipulation via stale session data or
                # admin price changes between cart add and checkout.
                product = item['product']
                variant = item.get('variant')
                if variant is not None:
                    current_price = variant.effective_price
                else:
                    current_price = product.price

                OrderItem.objects.create(order=order,
                                         product=product,
                                         price=current_price,
                                         quantity=item['quantity'],
                                         color=item['color_name'],
                                         size=item['size_name'])
            
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

            # M-3: Rotate session key to prevent session fixation.
            # An attacker who captured the old session cookie loses access.
            request.session.cycle_key()

            # C-2: Bind the order to the new session key.
            # payment_process() will verify this to prevent IDOR.
            order.session_key = request.session.session_key
            order.save(update_fields=['session_key'])

            # Set the order in the session (after cycle_key so keys match)
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
