# FILE: check_sender.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("🔍 CHECK BREVO SENDER VERIFICATION")
print("=" * 60)

BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '').strip()
SENDER_EMAIL = os.environ.get('MAIL_USERNAME', '').strip()

if not BREVO_API_KEY or not SENDER_EMAIL:
    print("❌ Missing API key or sender email in .env file")
    exit(1)

# Get list of verified senders
url = "https://api.brevo.com/v3/senders"
headers = {"api-key": BREVO_API_KEY, "accept": "application/json"}

try:
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        senders = data.get('senders', [])
        
        print(f"\n📋 Verified Senders ({len(senders)}):")
        verified = False
        for sender in senders:
            email = sender.get('email')
            status = sender.get('status', 'unknown')
            print(f"   - {email} ({status})")
            if email == SENDER_EMAIL and status == 'valid':
                verified = True
        
        if verified:
            print(f"\n✅ Your sender email {SENDER_EMAIL} is VERIFIED!")
        else:
            print(f"\n❌ Your sender email {SENDER_EMAIL} is NOT VERIFIED or NOT FOUND")
            print("\n   To verify your sender email:")
            print("   1. Go to https://app.brevo.com")
            print("   2. Navigate to: SMTP & API → Senders")
            print("   3. Click 'Add a new sender'")
            print("   4. Enter your email address")
            print("   5. Click the verification link sent to your email")
    else:
        print(f"❌ API Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Error: {e}")