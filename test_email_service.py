# FILE: test_email_service.py
from email_service import EmailService

# Test configuration
print(f"Configured: {EmailService.is_configured()}")

# Send a test email
EmailService.send_verification_email(
    user_name="Test User",
    user_email="ogwogp@gmail.com",
    student_id="STU001",
    verification_code="123456"
)

print("Email sent! Check your inbox.")