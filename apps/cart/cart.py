from decimal import Decimal
from django.conf import settings
from apps.catalog.models import Product


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, update_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': str(product.price)}
        
        if update_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        
        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        
        # Create a map of product_id -> Product object for efficient lookup
        product_map = {str(p.id): p for p in products}
        
        cart = self.cart.copy()
        
        for product_id, item in cart.items():
            # Create a shallow copy of the item to avoid mutating the session
            item_copy = item.copy()
            
            # Convert price to Decimal for calculation/display
            item_copy['price'] = Decimal(item['price'])
            item_copy['total_price'] = item_copy['price'] * item_copy['quantity']
            
            # Attach the product object using the map
            # Use .get() to handle potential missing products gracefully
            item_copy['product'] = product_map.get(product_id)
            
            yield item_copy

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.save()
