from decimal import Decimal
from django.conf import settings
from apps.catalog.models import Product


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        
        # Normalize legacy cart items (backward compatibility)
        modified = False
        normalized_cart = {}
        for key, item in cart.items():
            if not isinstance(item, dict):
                modified = True
                continue
            
            # If item is from the old structure (keys were product IDs as strings, e.g. "2")
            if 'product_id' not in item:
                parts = key.split('_')
                try:
                    product_id = int(parts[0])
                except (ValueError, IndexError):
                    modified = True
                    continue
                
                # Retrieve variant and size IDs if present
                variant_id = None
                if len(parts) > 1 and parts[1]:
                    try:
                        variant_id = int(parts[1])
                    except ValueError:
                        pass
                
                size_id = None
                if len(parts) > 2 and parts[2]:
                    try:
                        size_id = int(parts[2])
                    except ValueError:
                        pass
                
                # Convert the old item to the new format
                item['product_id'] = product_id
                item['variant_id'] = variant_id
                item['size_id'] = size_id
                
                normalized_key = '_'.join([str(product_id), str(variant_id) if variant_id else '', str(size_id) if size_id else ''])
                normalized_cart[normalized_key] = item
                modified = True
            else:
                normalized_cart[key] = item
                
        if modified:
            self.session[settings.CART_SESSION_ID] = normalized_cart
            self.session.modified = True
            self.cart = normalized_cart
        else:
            self.cart = cart

    def add(self, product, quantity=1, update_quantity=False, variant_id=None, size_id=None):
        parts = [str(product.id), str(variant_id) if variant_id else '', str(size_id) if size_id else '']
        item_key = '_'.join(parts)

        # Determine price
        price = product.price
        if variant_id:
            try:
                from apps.catalog.models import ProductVariant
                variant = ProductVariant.objects.get(id=variant_id)
                price = variant.effective_price
            except ProductVariant.DoesNotExist:
                pass

        if item_key not in self.cart:
            self.cart[item_key] = {
                'quantity': 0,
                'price': str(price),
                'product_id': product.id,
                'variant_id': int(variant_id) if variant_id else None,
                'size_id': int(size_id) if size_id else None
            }
        
        if update_quantity:
            self.cart[item_key]['quantity'] = quantity
        else:
            self.cart[item_key]['quantity'] += quantity
        
        self.save()

    def update_quantity(self, item_key, quantity):
        if item_key in self.cart:
            self.cart[item_key]['quantity'] = quantity
            self.save()

    def save(self):
        self.session.modified = True

    def remove(self, item_key):
        if item_key in self.cart:
            del self.cart[item_key]
            self.save()

    def __iter__(self):
        # Gather all IDs to perform single query lookups
        product_ids = {int(item['product_id']) for item in self.cart.values()}
        variant_ids = {int(item['variant_id']) for item in self.cart.values() if item.get('variant_id')}
        size_ids = {int(item['size_id']) for item in self.cart.values() if item.get('size_id')}

        products = Product.objects.filter(id__in=product_ids).prefetch_related('images')
        product_map = {p.id: p for p in products}

        variants = {}
        if variant_ids:
            from apps.catalog.models import ProductVariant
            variants = {
                v.id: v for v in ProductVariant.objects.filter(id__in=variant_ids)
                .select_related('color', 'product')
                .prefetch_related('images')
            }

        sizes = {}
        if size_ids:
            from apps.catalog.models import Size
            sizes = {s.id: s for s in Size.objects.filter(id__in=size_ids)}

        cart = self.cart.copy()
        for item_key, item in cart.items():
            item_copy = item.copy()
            item_copy['item_key'] = item_key

            product = product_map.get(int(item['product_id']))
            item_copy['product'] = product

            variant = variants.get(int(item['variant_id'])) if item.get('variant_id') else None
            item_copy['variant'] = variant

            size = sizes.get(int(item['size_id'])) if item.get('size_id') else None
            item_copy['size'] = size

            # Always use current price from DB (not from session) to prevent stale prices
            if variant is not None:
                current_price = variant.effective_price
            elif product is not None:
                current_price = product.price
            else:
                current_price = Decimal(item['price'])  # fallback if product deleted

            item_copy['price'] = current_price
            item_copy['total_price'] = current_price * item_copy['quantity']

            # Attach helper names directly
            item_copy['color_name'] = variant.color.name if (variant and variant.color) else ''
            item_copy['size_name'] = size.name if size else ''

            yield item_copy

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        """Calculate total using current DB prices via __iter__."""
        return sum(item['total_price'] for item in self)

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.save()
