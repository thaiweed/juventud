from django.shortcuts import render, redirect
from django.urls import reverse
from .models import OrderItem
from .forms import OrderCreateForm
from apps.cart.cart import Cart

def order_create(request):
    cart = Cart(request)
    if len(cart) == 0:
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
            # Redirect to payment process (to be implemented)
            # For now, we'll configure the URL, but the view will live in 'payments' app
            # Assuming 'payments:process' will take order_id in session or arg
            
            # Store order_id in session for payment processing
            request.session['order_id'] = order.id
            return redirect('payments:process')
    else:
        form = OrderCreateForm()
    
    return render(request, 'orders/order/create.html',
                  {'cart': cart, 'form': form})
