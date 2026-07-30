"""
diagnose_email.py — standalone test of your Gmail SMTP credentials,
completely independent of Flask. Run this from your project root:

    python diagnose_email.py

It will tell you exactly where it fails: DNS, connection, login, or send.
"""
import os
import smtplib
import socket
import ssl
from dotenv import load_dotenv

load_dotenv()

server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
port = int(os.environ.get('MAIL_PORT', 465))
username = os.environ.get('MAIL_USERNAME', 'scholarsubmit1@gmail.com').strip()
password = os.environ.get('MAIL_PASSWORD', 'luxtxnotbllnpcaj').strip()

print('=' * 60)
print('SUBMITA EMAIL DIAGNOSTIC')
print('=' * 60)
print(f'Server:   {server}')
print(f'Port:     {port}')
print(f'Username: {username or "❌ NOT SET"}')
print(f'Password: {"✓ set, length " + str(len(password)) if password else "❌ NOT SET"}')
print()

if not username or not password:
    print('❌ STOP: MAIL_USERNAME or MAIL_PASSWORD is missing from .env')
    print('   Check the file is named exactly ".env" (not ".env.txt") and')
    print('   sits in the same folder as run.py.')
    raise SystemExit(1)

# Step 1: DNS resolution
print('[1/4] Resolving smtp.gmail.com...')
try:
    ip = socket.gethostbyname(server)
    print(f'      ✅ Resolved to {ip}')
except socket.gaierror as e:
    print(f'      ❌ DNS resolution failed: {e}')
    print('      This usually means no internet connection, or a DNS/firewall block.')
    raise SystemExit(1)

# Step 2: raw socket connection to the port
print(f'[2/4] Testing raw connection to {server}:{port}...')
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    result = sock.connect_ex((server, port))
    sock.close()
    if result == 0:
        print(f'      ✅ Port {port} is open')
    else:
        print(f'      ❌ Port {port} appears BLOCKED (error code {result})')
        print('      A firewall, antivirus, or your network provider may be blocking outbound SMTP.')
        print('      Try a different network (e.g. a phone hotspot) to confirm.')
        raise SystemExit(1)
except Exception as e:
    print(f'      ❌ Connection test failed: {e}')
    raise SystemExit(1)

# Step 3: SSL + login
print('[3/4] Connecting with SSL and logging in...')
try:
    context = ssl.create_default_context()
    conn = smtplib.SMTP_SSL(server, port, context=context, timeout=15)
    conn.login(username, password)
    print('      ✅ Login successful')
except smtplib.SMTPAuthenticationError as e:
    print(f'      ❌ AUTHENTICATION FAILED: {e}')
    print()
    print('      Most common cause: MAIL_PASSWORD is your normal Gmail password,')
    print('      not an App Password. Gmail requires an App Password for SMTP:')
    print('      1. Enable 2-Step Verification on the Google account first')
    print('         (https://myaccount.google.com/security)')
    print('      2. Then generate an App Password at')
    print('         https://myaccount.google.com/apppasswords')
    print('      3. Use that 16-character password (no spaces) as MAIL_PASSWORD')
    raise SystemExit(1)
except Exception as e:
    print(f'      ❌ Connection/login failed: {e}')
    raise SystemExit(1)

# Step 4: send an actual test email
test_recipient = input('\n[4/4] Enter an email address to send a real test message to: ').strip()
if test_recipient:
    try:
        from email.mime.text import MIMEText
        msg = MIMEText('If you received this, your Submita email configuration works correctly.')
        msg['Subject'] = 'Submita SMTP test'
        msg['From'] = username
        msg['To'] = test_recipient
        conn.send_message(msg)
        print(f'      ✅ Test email sent to {test_recipient} — check the inbox (and spam folder)')
    except Exception as e:
        print(f'      ❌ Send failed: {e}')

conn.quit()
print('\n' + '=' * 60)
print('DIAGNOSTIC COMPLETE')
print('=' * 60)
