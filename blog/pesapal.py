import uuid
import requests
from django.conf import settings
from .models import normalize_phone

# Sandbox endpoint — change to live URL when you're ready
PESAPAL_API_BASE = 'https://pay.pesapal.com/v3'

# You can also move these to your settings.py
PESAPAL_CONSUMER_KEY = 'xw/q8cC95PDOQF0quZipAHrlqKT87xHq'
PESAPAL_CONSUMER_SECRET = 'Z+3ylSuAClDicysugGURu8drEuE='

def get_access_token():
    url = f"{PESAPAL_API_BASE}/api/Auth/RequestToken"
    headers = {'Content-Type': 'application/json'}
    data = {
        'consumer_key': PESAPAL_CONSUMER_KEY,
        'consumer_secret': PESAPAL_CONSUMER_SECRET
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get('token')
    else:
        raise Exception(f"Access token error: {response.text}")


def make_order(user_email, amount, phone_number, callback_url):
    token = get_access_token()

    url = f"{PESAPAL_API_BASE}/api/Transactions/SubmitOrderRequest"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    order_id = str(uuid.uuid4())
    normalized_phone = normalize_phone(phone_number)

    payload = {
        "id": order_id,
        "currency": "KES",
        "amount": amount,
        "description": "KaziFlow Monthly Subscription",
        "callback_url": callback_url,
        "notification_id": settings.PESAPAL_IPN_ID,  # IPN is optional unless you're using it
        "merchant_reference": normalized_phone,  # ✅ THIS IS WHAT PESA RETURNS TO CALLBACK
        "billing_address": {
            "email_address": user_email,
            "phone_number":normalized_phone,
            "country_code": "KE",
            "first_name": "Customer",
            "last_name": "User",
            "line_1": "Online",
            "city": "Nairobi",
            "state": "Nairobi"
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    print("Raw Pesapal response:", response.text)

    try:
        data = response.json()
    except ValueError:
        raise Exception(f"Invalid JSON from Pesapal: {response.text}")

    if response.status_code == 200 and data and 'redirect_url' in data:
        return {
            'order_tracking_id': data.get('order_tracking_id'),
            'redirect_url': data.get('redirect_url'),
            'merchant_reference': phone_number
        }
    else:
        raise Exception(f"Pesapal order error: {data or response.text}")

def get_transaction_status(tracking_id):
    token = get_access_token()
    url = f"{PESAPAL_API_BASE}/api/Transactions/GetTransactionStatus?orderTrackingId={tracking_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    return response.json()

def register_ipn_url():
    token = get_access_token()

    url = "https://pay.pesapal.com/v3/api/URLSetup/RegisterIPN"

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    data = {
        "url": "https://1a64-2c0f-fe38-2250-366c-6641-c444-87ed-f9fc.ngrok-free.app/pesapal-callback/",  # replace with your actual callback
        "ipn_notification_type": "POST"
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        return response.json().get('ipn_id')
    else:
        raise Exception(f"Failed to register IPN: {response.text}")
