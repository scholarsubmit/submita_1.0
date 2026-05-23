# FILE: check_brevo_status.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("🔍 BREVO ACCOUNT STATUS")
print("=" * 60)

API_KEY = os.environ.get('BREVO_API_KEY', '').strip()
SENDER_EMAIL = os.environ.get('MAIL_USERNAME', '').strip()

print(f"\nSender Email: {SENDER_EMAIL}")
print(f"API Key: {API_KEY[:15]}...")

# Check account info
headers = {"api-key": API_KEY, "accept": "application/json"}

# 1. Get account info
print("\n📡 Fetching account info...")
resp = requests.get("https://api.brevo.com/v3/account", headers=headers)

if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Account: {data.get('email')}")
    print(f"   Plan: {data.get('plan', [{}])[0].get('plan_type', 'N/A')}")
    print(f"   Credits: {data.get('plan', [{}])[0].get('credits', 'N/A')}")
else:
    print(f"❌ Error: {resp.status_code} - {resp.text}")
    exit(1)

# 2. Get verified senders
print("\n📡 Fetching verified senders...")
resp = requests.get("https://api.brevo.com/v3/senders", headers=headers)

if resp.status_code == 200:
    data = resp.json()
    senders = data.get('senders', [])
    
    print(f"\n📋 Verified Senders ({len(senders)}):")
    verified = False
    for sender in senders:
        email = sender.get('email')
        status = sender.get('status')
        print(f"   - {email} ({status})")
        if email == SENDER_EMAIL and status == 'valid':
            verified = True
    
    if verified:
        print(f"\n✅ Your sender '{SENDER_EMAIL}' is VERIFIED!")
    else:
        print(f"\n❌ Your sender '{SENDER_EMAIL}' is NOT VERIFIED!")
        print("\n   To verify:")
        print("   1. Go to https://app.brevo.com")
        print("   2. Click your profile → SMTP & API → Senders")
        print("   3. Click 'Add a new sender'")
        print("   4. Enter your email address")
        print("   5. Click the verification link in your email")
else:
    print(f"❌ Error: {resp.status_code}")