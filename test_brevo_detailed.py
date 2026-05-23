# FILE: test_brevo_detailed.py
import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("📧 BREVO DETAILED EMAIL TEST")
print("=" * 60)

BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '').strip()
SENDER_EMAIL = os.environ.get('MAIL_USERNAME', '').strip()
RECIPIENT_EMAIL = os.environ.get('TEST_RECIPIENT_EMAIL', 'ogwogp@gmail.com')

print(f"\n📋 Configuration:")
print(f"   Sender: {SENDER_EMAIL}")
print(f"   Recipient: {RECIPIENT_EMAIL}")
print(f"   API Key: {BREVO_API_KEY[:15]}...")

if not BREVO_API_KEY or not SENDER_EMAIL:
    print("\n❌ Missing configuration")
    exit(1)

url = "https://api.brevo.com/v3/smtp/email"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "api-key": BREVO_API_KEY
}

# Simple, clean HTML email
payload = {
    "sender": {
        "name": "Submita Platform",
        "email": SENDER_EMAIL
    },
    "to": [
        {
            "email": RECIPIENT_EMAIL,
            "name": "Test User"
        }
    ],
    "subject": "📧 Test Email from Submita - Please Verify",
    "htmlContent": """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; }
            .container { max-width: 500px; margin: 0 auto; padding: 20px; }
            .header { background: #10b981; padding: 20px; text-align: center; color: white; }
            .content { padding: 20px; background: #f9fafb; }
            .footer { text-align: center; padding: 20px; font-size: 12px; color: #6b7280; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>✅ Email Test from Submita</h2>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p>This is a test email from the <strong>Submita Assignment Platform</strong>.</p>
                <p>If you received this email, your email configuration is working correctly!</p>
                <hr>
                <p><small>Sent at: """ + time.strftime('%Y-%m-%d %H:%M:%S') + """</small></p>
            </div>
            <div class="footer">
                <p>© 2026 Submita - Assignment Management Platform</p>
            </div>
        </div>
    </body>
    </html>
    """
}

print("\n📡 Sending email...")

try:
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    
    print(f"\n📊 Response Status: {response.status_code}")
    print(f"📊 Response Body: {response.text}")
    
    if response.status_code in [200, 201, 202]:
        response_data = response.json()
        message_id = response_data.get('messageId', 'unknown')
        print(f"\n✅ Email ACCEPTED by Brevo!")
        print(f"   Message ID: {message_id}")
        print(f"\n   📌 IMPORTANT: Brevo accepted the email, but delivery depends on:")
        print(f"      1. Sender verification status")
        print(f"      2. Recipient spam filters")
        print(f"      3. Brevo's delivery queue")
        print(f"\n   💡 Check your spam/junk folder.")
        print(f"   💡 Wait 2-5 minutes for delivery.")
        print(f"   💡 If still not received, verify your sender email in Brevo dashboard.")
    else:
        print(f"\n❌ Email REJECTED by Brevo")
        
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 60)