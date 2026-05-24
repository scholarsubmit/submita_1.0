# test_email_465.py
# Google SMTP on PORT 465 (SSL) - CORRECTED VERSION

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("=" * 60)
print("TESTING GMAIL SMTP ON PORT 465 (SSL)")
print("=" * 60)

# Get credentials from .env
EMAIL = os.environ.get('MAIL_USERNAME', '').strip()
PASSWORD = os.environ.get('MAIL_PASSWORD', '').strip()

print(f"Email: {EMAIL}")
print(f"Password: {'✓ SET' if PASSWORD else '✗ MISSING'} (length: {len(PASSWORD) if PASSWORD else 0})")

if not EMAIL or not PASSWORD:
    print("\n❌ ERROR: Missing email credentials in .env file!")
    print("\nAdd to .env:")
    print("MAIL_USERNAME=your_email@gmail.com")
    print("MAIL_PASSWORD=your_16_char_app_password")
    exit(1)

# Get recipient email
to_email = input("\nEnter email address to send test: ").strip()

if not to_email:
    print("No email entered!")
    exit(1)

# Email content
subject = "Submita - SMTP Test (Port 465 SSL)"
body = f"""
Hello,

This is a test email from Submita using Gmail SMTP on PORT 465 (SSL).

If you received this, your email configuration is working!

Timestamp: {__import__('datetime').datetime.now()}

Best regards,
Submita Team
"""

html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #059669; padding: 20px; text-align: center; color: white; }}
        .content {{ padding: 20px; }}
        .success {{ color: #059669; font-size: 24px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Test Successful!</h1>
        </div>
        <div class="content">
            <p class="success">Port 465 SSL is WORKING!</p>
            <p>This email was sent using Gmail SMTP on port 465 with SSL encryption.</p>
            <p>Time: {__import__('datetime').datetime.now()}</p>
            <hr>
            <p style="color: #666; font-size: 12px;">Submita Assignment Platform</p>
        </div>
    </div>
</body>
</html>
"""

try:
    print(f"\n📧 Attempting to send to {to_email}...")
    print(f"   Using: smtp.gmail.com:465 (SSL)")
    
    # Create message
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # Attach both plain text and HTML
    msg.attach(MIMEText(body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))
    
    # IMPORTANT: Use SMTP_SSL for port 465 (NOT starttls)
    print("\n1. Creating SSL connection...")
    context = ssl.create_default_context()
    
    print("2. Connecting to smtp.gmail.com:465...")
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
        
        print("3. Connection established!")
        print("4. Logging in...")
        server.login(EMAIL, PASSWORD)
        print("   ✓ Login successful!")
        
        print("5. Sending email...")
        server.send_message(msg)
        print("   ✓ Message sent!")
        
        print("6. Closing connection...")
    
    print("\n" + "=" * 60)
    print("✅✅✅ EMAIL SENT SUCCESSFULLY! ✅✅✅")
    print("=" * 60)
    print(f"\n📬 Check {to_email} inbox (and spam folder)")
    print("   Email should arrive within 1-2 minutes")
    
except smtplib.SMTPAuthenticationError as e:
    print(f"\n❌ AUTHENTICATION FAILED!")
    print(f"   Error: {e}")
    print("\n   SOLUTION:")
    print("   1. You MUST use an App Password from Google")
    print("   2. Regular Gmail password will NOT work")
    print("   3. Go to: https://myaccount.google.com/apppasswords")
    print("   4. Generate App Password for 'Mail'")
    print("   5. Copy the 16-character password to .env")
    
except smtplib.SMTPServerDisconnected as e:
    print(f"\n❌ SERVER DISCONNECTED!")
    print(f"   Error: {e}")
    print("\n   Possible causes:")
    print("   - Firewall blocking port 465")
    print("   - Antivirus blocking SMTP")
    print("   - Network restrictions")
    
except TimeoutError as e:
    print(f"\n❌ TIMEOUT ERROR!")
    print(f"   Error: {e}")
    print("\n   Port 465 is BLOCKED or unreachable!")
    print("   Try:")
    print("   1. Disable Windows Firewall temporarily")
    print("   2. Disable antivirus temporarily")
    print("   3. Try a different network (mobile hotspot)")
    print("   4. Or use Brevo API instead")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()