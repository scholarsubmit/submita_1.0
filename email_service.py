# FILE: email_service.py - FIXED (No shutdown errors)
# PURE GOOGLE SMTP - PORT 465 SSL

import threading
import os
import smtplib
import ssl
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import url_for, current_app
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class EmailService:
    """Handles all email operations using Google SMTP on port 465 (SSL)"""
    
    # Google SMTP Configuration - PORT 465 SSL
    SMTP_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('MAIL_PORT', 465))
    SMTP_USERNAME = os.environ.get('MAIL_USERNAME', '').strip()
    SMTP_PASSWORD = os.environ.get('MAIL_PASSWORD', '').strip()
    
    SENDER_NAME = os.environ.get('MAIL_SENDER_NAME', 'Submita')
    SENDER_EMAIL = SMTP_USERNAME
    
    @classmethod
    def is_configured(cls):
        """Check if email service is properly configured"""
        configured = bool(cls.SMTP_USERNAME and cls.SMTP_PASSWORD)
        if not configured:
            print(f"❌ Email not configured!")
            print(f"   MAIL_USERNAME: {'✓' if cls.SMTP_USERNAME else '✗'}")
            print(f"   MAIL_PASSWORD: {'✓' if cls.SMTP_PASSWORD else '✗'}")
        return configured
    
    @staticmethod
    def send_email_sync(recipient, subject, html_content, text_content=None):
        """Send email synchronously (no threading issues)"""
        
        if not EmailService.is_configured():
            print(f"❌ Email not sent - Missing Gmail configuration")
            return False
        
        try:
            EmailService._send_email_direct(recipient, subject, html_content, text_content)
            return True
        except Exception as e:
            print(f"❌ Email failed: {e}")
            return False
    
    @staticmethod
    def send_email_async(recipient, subject, html_content, text_content=None):
        """Send email asynchronously (for web requests)"""
        
        if not EmailService.is_configured():
            print(f"❌ Email not sent - Missing Gmail configuration")
            return False
        
        try:
            app_context = current_app._get_current_object()
        except RuntimeError:
            app_context = None
        
        # Use non-daemon thread
        thread = threading.Thread(
            target=EmailService._send_email_with_context,
            args=(recipient, subject, html_content, text_content, app_context)
        )
        thread.daemon = False
        thread.start()
        
        return True
    
    @staticmethod
    def _send_email_with_context(recipient, subject, html_content, text_content, app_context):
        """Send email with Flask context"""
        if app_context:
            with app_context.app_context():
                EmailService._send_email_direct(recipient, subject, html_content, text_content)
        else:
            EmailService._send_email_direct(recipient, subject, html_content, text_content)
    
    @staticmethod
    def _send_email_direct(recipient, subject, html_content, text_content):
        """Direct email sending using Google SMTP with SSL on port 465"""
        try:
            print(f"\n📧 Gmail SSL: Sending to {recipient}")
            print(f"   Server: {EmailService.SMTP_SERVER}:{EmailService.SMTP_PORT}")
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{EmailService.SENDER_NAME} <{EmailService.SMTP_USERNAME}>"
            msg['To'] = recipient
            msg['Reply-To'] = EmailService.SMTP_USERNAME
            
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Create SSL context and connect
            context = ssl.create_default_context()
            
            print("   Connecting with SSL...")
            with smtplib.SMTP_SSL(EmailService.SMTP_SERVER, EmailService.SMTP_PORT, context=context) as server:
                print("   Connection established!")
                print("   Logging in...")
                server.login(EmailService.SMTP_USERNAME, EmailService.SMTP_PASSWORD)
                print("   ✓ Login successful!")
                print("   Sending message...")
                server.send_message(msg)
                print("   ✓ Message sent!")
            
            print(f"✅ Email sent successfully to {recipient}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"\n❌ AUTHENTICATION FAILED!")
            print(f"   Error: {e}")
            print("\n   SOLUTION: You MUST use an App Password from Google")
            return False
            
        except smtplib.SMTPServerDisconnected as e:
            print(f"\n❌ SERVER DISCONNECTED!")
            print(f"   Error: {e}")
            return False
            
        except TimeoutError as e:
            print(f"\n❌ TIMEOUT ERROR!")
            print(f"   Error: {e}")
            return False
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return False
    
    # ==================== EMAIL TEMPLATES ====================
    
    @staticmethod
    def send_lecturer_verification_email(lecturer_data, verification_code, expires_at):
        """Send lecturer verification code email"""
        base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
        registration_link = f"{base_url}/register"
        
        if len(verification_code) > 6:
            formatted_code = ' '.join([verification_code[i:i+3] for i in range(0, len(verification_code), 3)])
        else:
            formatted_code = verification_code
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 550px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #059669, #047857); padding: 25px; text-align: center; color: white; border-radius: 10px 10px 0 0; }}
                .content {{ background: #fff; padding: 30px; border: 1px solid #e5e7eb; border-radius: 0 0 10px 10px; }}
                .code-box {{ background: #f0fdf4; border: 3px solid #059669; border-radius: 12px; padding: 25px; text-align: center; margin: 20px 0; }}
                .code {{ font-size: 36px; font-weight: bold; color: #047857; font-family: monospace; letter-spacing: 5px; }}
                .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 8px; }}
                .button {{ background: #059669; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; display: inline-block; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Lecturer Verification Code</h1>
                    <p>Submita Assignment Platform</p>
                </div>
                <div class="content">
                    <p>Dear <strong>{lecturer_data['full_name']}</strong>,</p>
                    <p>You have been invited to join Submita as a lecturer.</p>
                    
                    <div class="code-box">
                        <p><strong>Your Verification Code:</strong></p>
                        <div class="code">{formatted_code}</div>
                        <p>🔑 {len(verification_code)}-character code</p>
                    </div>
                    
                    <div class="warning">
                        <strong>⚠️ Important Security Notice:</strong>
                        <ul style="margin-top: 10px; padding-left: 20px;">
                            <li>This code expires on <strong>{expires_at.strftime('%Y-%m-%d at %H:%M')}</strong></li>
                            <li>This code can only be used once</li>
                            <li>Never share this code with anyone</li>
                        </ul>
                    </div>
                    
                    <div style="text-align: center; margin: 25px 0;">
                        <a href="{registration_link}" class="button">Complete Registration →</a>
                    </div>
                    
                    <p style="color: #666; font-size: 12px; text-align: center;">Staff ID: {lecturer_data.get('staff_id', 'N/A')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        SUBMITA LECTURER VERIFICATION CODE
        
        Dear {lecturer_data['full_name']},
        
        Your Verification Code: {verification_code}
        Staff ID: {lecturer_data.get('staff_id', 'N/A')}
        
        This code expires on: {expires_at.strftime('%Y-%m-%d at %H:%M')}
        
        Complete your registration at: {registration_link}
        
        Security Notes:
        - This code can only be used once
        - Never share this code with anyone
        
        © 2026 Submita
        """
        
        print(f"\n📧 Sending lecturer verification email")
        print(f"   To: {lecturer_data['email']}")
        print(f"   Name: {lecturer_data['full_name']}")
        print(f"   Code: {verification_code}")
        
        return EmailService.send_email_sync(lecturer_data['email'], "🔐 Submita Lecturer Verification Code", html_content, text_content)
    
    @staticmethod
    def send_verification_email(user_name, user_email, student_id, verification_code):
        """Send student verification email"""
        base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
        verification_link = f"{base_url}/verify"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #059669, #047857); padding: 30px; text-align: center; color: white; border-radius: 10px 10px 0 0; }}
                .code {{ background: #f0fdf4; border: 2px dashed #059669; border-radius: 10px; padding: 20px; text-align: center; margin: 20px 0; }}
                .code-value {{ font-size: 32px; font-weight: bold; color: #047857; letter-spacing: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Submita!</h1>
                </div>
                <div class="content">
                    <p>Hello <strong>{user_name}</strong>,</p>
                    <p>Your verification code is:</p>
                    <div class="code">
                        <div class="code-value">{verification_code}</div>
                    </div>
                    <p>Your Student ID: <strong>{student_id}</strong></p>
                    <p><a href="{verification_link}">Verify your account here</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email_sync(user_email, "Verify Your Submita Account", html_content)
    
    @staticmethod
    def send_grade_notification(student_email, student_name, assignment_title, grade, feedback=None):
        """Send grade notification email"""
        base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
        dashboard_link = f"{base_url}/student-dashboard"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .grade {{ font-size: 48px; font-weight: bold; color: #059669; text-align: center; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Assignment Graded!</h2>
                <p>Hello <strong>{student_name}</strong>,</p>
                <p>Your assignment "<strong>{assignment_title}</strong>" has been graded.</p>
                <div class="grade">{grade}%</div>
                {f'<p><strong>Feedback:</strong><br>{feedback}</p>' if feedback else ''}
                <p><a href="{dashboard_link}">View Dashboard</a></p>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email_sync(student_email, f"Grade Posted: {assignment_title}", html_content)


# Test function
def test_email_config():
    print("\n" + "=" * 60)
    print("📧 TESTING GOOGLE SMTP - PORT 465 SSL")
    print("=" * 60)
    print(f"Server: {EmailService.SMTP_SERVER}:{EmailService.SMTP_PORT}")
    print(f"Username: {EmailService.SMTP_USERNAME}")
    print(f"Password: {'✓ Set' if EmailService.SMTP_PASSWORD else '✗ Missing'}")
    print(f"Sender Name: {EmailService.SENDER_NAME}")
    
    if not EmailService.is_configured():
        print("\n❌ Email not configured!")
        return
    
    test_email = input("\n📧 Enter email address to send test: ").strip()
    if test_email:
        result = EmailService.send_email_sync(
            test_email,
            "Submita - SMTP Test (Port 465 SSL)",
            "<h1 style='color:#059669'>✅ Test Successful!</h1><p>Your Google SMTP configuration on port 465 SSL is working correctly.</p><p>You can now send lecturer verification codes.</p>",
            "Test Successful! Your Google SMTP configuration on port 465 SSL is working correctly."
        )
        if result:
            print(f"\n✅ Test email sent successfully to {test_email}")
            print("\n📬 Check your inbox/spam folder for the test email.")
        else:
            print(f"\n❌ Test email failed to send.")


if __name__ == '__main__':
    test_email_config()