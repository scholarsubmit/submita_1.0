# FILE: test_brevo_sdk.py
# LOCATION: /test_brevo_sdk.py
# FIXED: Better error handling and timeout

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("📧 BREVO SDK TEST")
print("=" * 60)

# Check environment variables
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '').strip()
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '').strip()

print(f"\n📋 Configuration:")
print(f"   BREVO_API_KEY: {'✅ Set (' + BREVO_API_KEY[:10] + '...)' if BREVO_API_KEY else '❌ MISSING'}")
print(f"   MAIL_USERNAME: {MAIL_USERNAME if MAIL_USERNAME else '❌ MISSING'}")

if not BREVO_API_KEY:
    print("\n❌ ERROR: BREVO_API_KEY not found in .env file")
    print("   Please add: BREVO_API_KEY=your-api-key-here")
    sys.exit(1)

if not MAIL_USERNAME:
    print("\n❌ ERROR: MAIL_USERNAME not found in .env file")
    print("   Please add: MAIL_USERNAME=your-verified-email@example.com")
    sys.exit(1)

try:
    print("\n📡 Importing Brevo SDK...")
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException
    print("   ✅ SDK imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import SDK: {e}")
    print("\n   Install with: pip install sib-api-v3-sdk")
    sys.exit(1)

try:
    print("\n🔧 Configuring API client...")
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    
    # Set timeout
    configuration.timeout = 30
    
    api_client = sib_api_v3_sdk.ApiClient(configuration)
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)
    print("   ✅ API client configured")
    
    # First, test the API key with a simple account call
    print("\n📡 Testing API key with account endpoint...")
    account_api = sib_api_v3_sdk.AccountApi(api_client)
    account_info = account_api.get_account()
    print(f"   ✅ API key is valid!")
    print(f"   Account: {account_info.email}")
    
except ApiException as e:
    print(f"   ❌ API Error: {e}")
    print(f"   Status: {e.status}")
    print(f"   Reason: {e.reason}")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Send test email
print("\n📡 Sending test email...")
print(f"   From: Submita Test <{MAIL_USERNAME}>")
print(f"   To: {MAIL_USERNAME}")

try:
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": MAIL_USERNAME, "name": "Test Recipient"}],
        sender={"email": MAIL_USERNAME, "name": "Submita Test"},
        subject="✅ Submita - Brevo SDK Test",
        html_content="""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .container { max-width: 500px; margin: 0 auto; padding: 20px; }
                .header { background: #059669; padding: 20px; text-align: center; color: white; }
                .content { padding: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>✅ Brevo SDK Test Successful!</h2>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>This test email confirms that your Brevo SDK integration is working correctly.</p>
                    <p>Time: """ + __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
                </div>
            </div>
        </body>
        </html>
        """
    )
    
    api_response = api_instance.send_transac_email(send_smtp_email)
    print(f"\n✅ SUCCESS! Email sent!")
    print(f"   Message ID: {api_response.message_id}")
    print(f"\n   Check your inbox or spam folder for the test email.")
    
except ApiException as e:
    print(f"\n❌ API Exception:")
    print(f"   Status: {e.status}")
    print(f"   Reason: {e.reason}")
    print(f"   Body: {e.body}")
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 60)
print("🏁 Test completed")
print("=" * 60)