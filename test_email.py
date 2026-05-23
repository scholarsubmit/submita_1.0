# FILE: diagnose_brevo.py
# LOCATION: /diagnose_brevo.py
# PURPOSE: Diagnose Brevo API key issues

import os
import requests
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("🔍 BREVO API DIAGNOSTIC TOOL")
print("=" * 60)

# Get API key
api_key = os.environ.get('BREVO_API_KEY', '').strip()
print(f"\n📋 API Key loaded: {'✅ Yes' if api_key else '❌ No'}")
if api_key:
    print(f"   Length: {len(api_key)} characters")
    print(f"   Starts with: {api_key[:10]}...")
    print(f"   Ends with: ...{api_key[-4:] if len(api_key) > 4 else ''}")
    
    # Check for common issues
    if ' ' in api_key:
        print("   ⚠️ WARNING: API key contains spaces!")
    if '\n' in api_key:
        print("   ⚠️ WARNING: API key contains newlines!")
    if not api_key.startswith('xkeysib-'):
        print("   ⚠️ WARNING: API key doesn't start with 'xkeysib-'")
else:
    print("\n❌ No API key found. Please add BREVO_API_KEY to .env file")
    exit(1)

# Test 1: Account endpoint (requires valid API key)
print("\n" + "=" * 60)
print("📡 TEST 1: Account API (Validates API Key)")
print("=" * 60)

account_url = "https://api.brevo.com/v3/account"
headers = {
    "accept": "application/json",
    "api-key": api_key
}

try:
    response = requests.get(account_url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ API KEY IS VALID!")
        print(f"   Account Email: {data.get('email', 'N/A')}")
        print(f"   Plan: {data.get('plan', [{}])[0].get('plan_type', 'N/A') if data.get('plan') else 'N/A'}")
    elif response.status_code == 401:
        print("❌ API KEY IS INVALID")
        print("   Please generate a new API key from Brevo dashboard")
    else:
        print(f"❌ Unexpected response: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Transactional email endpoint
print("\n" + "=" * 60)
print("📡 TEST 2: Transactional Email API")
print("=" * 60)

email_url = "https://api.brevo.com/v3/smtp/email"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "api-key": api_key
}

sender_email = os.environ.get('MAIL_USERNAME', '').strip()
recipient_email = os.environ.get('TEST_RECIPIENT_EMAIL', '').strip() or sender_email

if not sender_email:
    print("❌ No sender email configured. Add MAIL_USERNAME to .env")
else:
    payload = {
        "sender": {"email": sender_email, "name": "Brevo Test"},
        "to": [{"email": recipient_email}],
        "subject": "Brevo API Test",
        "htmlContent": "<p>This is a test email to verify your Brevo API key.</p>"
    }
    
    try:
        response = requests.post(email_url, json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code in [200, 201, 202]:
            print("✅ Transactional email test PASSED!")
            data = response.json()
            print(f"   Message ID: {data.get('messageId', 'N/A')}")
        elif response.status_code == 400:
            print("❌ Bad Request - Check sender email")
            print(f"   Error: {response.text}")
        elif response.status_code == 401:
            print("❌ Unauthorized - API key issue")
        elif response.status_code == 403:
            print("❌ Forbidden - Sender email not verified")
            print("   Please verify your sender email in Brevo dashboard")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("🏁 Diagnostic complete")
print("=" * 60)