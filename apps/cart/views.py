from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods
from django.http import HttpResponse, HttpResponseBadRequest
from django_ratelimit.decorators import ratelimit
from apps.catalog.models import Product
from .cart import Cart


# H-2: 30 cart additions per minute is generous for real users but stops bots
@ratelimit(key='ip', rate='30/m', method='POST', block=True)
@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    # H-3: validate quantity to prevent HTTP 500 on malformed input
    try:
        quantity = max(1, int(request.POST.get('quantity', 1)))
    except (ValueError, TypeError):
        return HttpResponseBadRequest('Invalid quantity')
    variant_id = request.POST.get('variant_id') or None
    size_id = request.POST.get('size') or None
    cart.add(product=product, quantity=quantity, variant_id=variant_id, size_id=size_id)
    
    response = render(request, 'cart/partials/cart_content.html', {'cart': cart})
    response['HX-Trigger'] = 'open-cart'
    return response


@require_POST
def cart_remove(request, item_key):
    cart = Cart(request)
    cart.remove(item_key)
    
    return render(request, 'cart/partials/cart_content.html', {'cart': cart})


@require_POST
def cart_update(request, item_key):
    cart = Cart(request)
    # H-3: validate quantity to prevent HTTP 500 on malformed input
    try:
        quantity = max(0, int(request.POST.get('quantity', 1)))
    except (ValueError, TypeError):
        return HttpResponseBadRequest('Invalid quantity')
    
    if quantity > 0:
        cart.update_quantity(item_key=item_key, quantity=quantity)
    else:
        cart.remove(item_key)
    
    return render(request, 'cart/partials/cart_content.html', {'cart': cart})


@require_http_methods(['GET'])
def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart/partials/cart_content.html', {'cart': cart})
