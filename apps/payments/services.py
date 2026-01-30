import requests
import json
import hmac
import hashlib
from django.conf import settings

class NowPaymentsService:
    API_URL = 'https://api.nowpayments.io/v1'

    def __init__(self):
        self.api_key = settings.NOWPAYMENTS_API_KEY
        self.ipn_secret = settings.NOWPAYMENTS_IPN_SECRET

    def create_invoice(self, order_id, price_amount, price_currency, order_description, ipn_callback_url, success_url, cancel_url):
        url = f"{self.API_URL}/invoice"
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        payload = {
            "price_amount": float(price_amount),
            "price_currency": price_currency,
            "order_id": str(order_id),
            "order_description": order_description,
            "ipn_callback_url": ipn_callback_url,
            "success_url": success_url,
            "cancel_url": cancel_url
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"NOWPayments API Error: {e}")
            if response.content:
                print(f"Response content: {response.content}")
            return None

    def check_signature(self, request_data, received_signature):
        # Sort keys
        sorted_keys = sorted(request_data.keys())
        sorted_dict = {k: request_data[k] for k in sorted_keys}
        
        # Convert to string similar to how NOWPayments expects it
        # Based on documentation: JSON.stringify(params, Object.keys(params).sort())
        # In Python: json.dumps(message, separators=(',', ':'), sort_keys=True)
        # However, the documentation example in Python uses:
        # sorted_msg = json.dumps(message, separators=(',', ':'), sort_keys=True)
        
        # Important: remove 'token_id' if present? Documentation doesn't explicitly say to remove fields
        # but standard HMAC usually involves creating string from sorted params.
        
        sorted_msg = json.dumps(sorted_dict, separators=(',', ':'), sort_keys=True)
        
        digest = hmac.new(
            str(self.ipn_secret).encode('utf-8'),
            sorted_msg.encode('utf-8'),
            hashlib.sha512
        )
        signature = digest.hexdigest()
        
        return signature == received_signature
