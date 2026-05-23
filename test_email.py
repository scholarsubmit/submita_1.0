# FILE: test_email.py
import os

import requests
import json

print("🔄 STEP 1: Script has started executing...")

# --- PASTE YOUR BREVO DETAILS HERE FOR THIS DIRECT ISOLATED TEST ---
BREVO_API_KEY=os.environ.get('BREVO_API_KEY')
MAIL_USERNAME=os.environ.get('MAIL_USERNAME')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
RECIPIENT_EMAIL = "ogwogp@gmail.com"  # Test sending anywhere globally!

print(f"🔄 STEP 2: Target Recipient set to: {RECIPIENT_EMAIL}")

# Brevo v3 REST Architecture Contract
API_URL = "https://api.brevo.com/v3/smtp/email"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "api-key": BREVO_API_KEY
}

payload = {
    "sender": {
        "name": "Submita Test Engine", 
        "email": SENDER_EMAIL
    },
    "to": [
        {
            "email": RECIPIENT_EMAIL,
            "name": "Test Recipient"
        }
    ],
    "subject": "Testing Pure HTTP Global Delivery",
    "htmlContent": """
        <html>
            <body>
                <h2 style='color: #059669;'>HTTP Gateway Verification</h2>
                <p>If you see this, your app bypassed all port restrictions successfully!</p>
            </body>
        </html>
    """
}

try:
    print("🔄 STEP 3: Dispatching raw HTTP POST payload over Port 443...")
    
    # Fire the web request directly to Brevo's cloud server
    response = requests.post(API_URL, data=json.dumps(payload), headers=headers, timeout=12)
    
    print(f"🔄 STEP 4: HTTP Status Code returned: {response.status_code}")
    
    if response.status_code in [200, 201, 202]:
        print("✅ SUCCESS! Brevo accepted the packet.")
        print(f"   API Response Data: {response.text}")
    else:
        print("❌ FAILED! Brevo API rejected the configuration details.")
        print(f"   Server Error Message: {response.text}")

except Exception as e:
    print(f"❌ CRITICAL FAILURE! Network exception occurred: {str(e)}")

print("🔄 STEP 5: Script reached the absolute end.")