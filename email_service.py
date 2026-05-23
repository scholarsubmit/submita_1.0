# FILE: email_service.py
# LOCATION: /email_service.py
# PIPELINE: Pure HTTP API requests (No SMTP, bypasses all cloud firewalls)

import threading
import os
import requests  # Using standard HTTP requests
from flask import url_for, current_app
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    """Handles all email operations asynchronously using pure HTTP REST APIs"""
    
    BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
    API_KEY = os.environ.get('BREVO_API_KEY', '')
    
    # You can change this to your custom domain email later. 
    # For now, Brevo allows you to use your registration email to test globally.
    SENDER_EMAIL = os.environ.get('MAIL_USERNAME', 'your-registered-brevo-email@gmail.com')
    
    @staticmethod
    def send_email_async(recipient, subject, html_content, text_content=None):
        """Send email via background thread to prevent blocking the Flask UI"""
        if not EmailService.API_KEY:
            print(f"❌ Email aborted - BREVO_API_KEY missing from environment.")
            return False
            
        try:
            app_context = current_app._get_current_object()
        except RuntimeError:
            app_context = None

        thread = threading.Thread(
            target=EmailService._send_email,
            args=(recipient, subject, html_content, text_content, app_context)
        )
        thread.daemon = True
        thread.start()
        return True
    
    @staticmethod
    def _send_email(recipient, subject, html_content, text_content, app_context=None):
        """Executes the outbound transactional HTTP POST payload securely over Port 443"""
        
        def execute_send():
            # Build headers required by Brevo's REST architecture
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": EmailService.API_KEY
            }
            
            # Map out Brevo's exact HTTP JSON contract payload
            payload = {
                "sender": {"name": "Submita", "email": EmailService.SENDER_EMAIL},
                "to": [{"email": recipient}],
                "subject": subject,
                "htmlContent": html_content
            }
            
            if text_content:
                payload["textContent"] = text_content
                
            try:
                # Fire the non-blocking HTTP post web request
                response = requests.post(EmailService.BREVO_API_URL, json=payload, headers=headers, timeout=10)
                
                if response.status_code in [200, 201, 202]:
                    print(f"✅ HTTP Email sent successfully to {recipient}! ID: {response.json().get('messageId')}")
                else:
                    print(f"❌ Brevo HTTP Error {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f"❌ Network request exception while calling Brevo HTTP API: {e}")

        if app_context:
            with app_context.app_context():
                execute_send()
        else:
            execute_send()

    # ==================== NOTIFICATION WRAPPERS ====================
    @staticmethod
    def send_verification_email(user_name, user_email, student_id, verification_code):
        """Send account verification email"""
        verification_link = url_for('verify', _external=True)
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>Welcome to Submita!</h2>
            <p>Hello <strong>{user_name}</strong>,</p>
            <p>Your verification code is: <strong style="font-size: 24px; color: #059669; letter-spacing: 2px;">{verification_code}</strong></p>
            <p>Your Student ID is: <strong>{student_id}</strong></p>
            <p><a href="{verification_link}" style="background: #059669; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Verify Account</a></p>
        </div>
        """
        EmailService.send_email_async(user_email, "Verify Your Submita Account", html_content)

    @staticmethod
    def send_otp(user_email, user_name, otp_code):
        """Send a transactional 6-digit login OTP code anywhere in the world"""
        html_content = f"""
        <div style="font-family: sans-serif; max-width: 400px; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px; margin: 0 auto;">
            <h2 style="color: #059669; text-align: center;">Your Login Code</h2>
            <p>Hello {user_name},</p>
            <p>Use this one-time token to access your account:</p>
            <div style="font-size: 32px; font-weight: bold; background: #f0fdf4; color: #047857; text-align: center; padding: 10px; border-radius: 6px; letter-spacing: 5px;">
                {otp_code}
            </div>
            <p style="font-size: 11px; color: #6b7280; text-align: center; margin-top: 15px;">Valid for 10 minutes.</p>
        </div>
        """
        EmailService.send_email_async(user_email, f"🔒 {otp_code} is your Submita code", html_content)