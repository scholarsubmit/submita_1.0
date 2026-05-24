# FILE: test_email_modes.py
import os
from dotenv import load_dotenv
load_dotenv()

# Test current mode
from email_service import EmailService

print(f"Current mode: {EmailService.get_mode()}")
print(f"Configured: {EmailService.is_configured()}")

# Send test email
EmailService.send_verification_email(
    user_name="Test User",
    user_email="ogwogp@gmail.com", 
    student_id="STU001",
    verification_code="123456"
)