import os
import django
import json
from decimal import Decimal
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.payments.services import NowPaymentsService
from apps.catalog.models import Product, Category

def test_integration():
    print("Starting integration test...")

    # 1. Create Data
    cat, _ = Category.objects.get_or_create(name='TestCat', slug='test-cat')
    product = Product.objects.create(
        category=cat,
        name='Test Product',
        slug='test-product-payment',
        price=Decimal('100.00'),
        description='Test desc'
    )
    
    # 2. Create Order
    print("Creating Order...")
    order = Order.objects.create(
        first_name='John',
        last_name='Doe',
        email='john@example.com',
        address='123 St',
        postal_code='12345',
        city='City'
    )
    OrderItem.objects.create(order=order, product=product, price=product.price, quantity=2)
    
    assert order.get_total_cost() == Decimal('200.00')
    print(f"Order created: {order}, Total: {order.get_total_cost()}")

    # 3. Create Payment
    print("Creating Payment...")
    payment = Payment.objects.create(
        order=order,
        payment_id='test_payment_id_123',
        price_amount=order.get_total_cost(),
        price_currency='usd'
    )
    print(f"Payment created: {payment}")

    # 4. Test Service Signature Verification
    print("Testing One-way Signature Verification...")
    service = NowPaymentsService()
    
    # Mock data as if received from IPN
    ipn_data = {
        'payment_id': 'test_payment_id_123',
        'payment_status': 'confirmed',
        'pay_amount': 200.0,
        'pay_currency': 'usd',
        'order_id': str(order.id)
        # Note: IPN sends many fields.
    }
    
    # We need to GENERATE a signature to test the CHECK signature function.
    # We can use the service's internal method concepts to generate valid sig.
    import hmac
    import hashlib
    
    # Sort and stringify just like NowPayments
    sorted_msg = json.dumps(ipn_data, separators=(',', ':'), sort_keys=True)
    secret = settings.NOWPAYMENTS_IPN_SECRET
    digest = hmac.new(
        str(secret).encode('utf-8'),
        sorted_msg.encode('utf-8'),
        hashlib.sha512
    )
    valid_signature = digest.hexdigest()
    
    # Now verify using our service method
    is_valid = service.check_signature(ipn_data, valid_signature)
    print(f"Signature check result (expected True): {is_valid}")
    
    if is_valid:
        print("SUCCESS: Integration test passed!")
    else:
        print("FAILURE: Signature verification failed.")

if __name__ == '__main__':
    try:
        test_integration()
    except Exception as e:
        print(f"ERROR: {e}")
