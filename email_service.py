# FILE: email_service.py
# LOCATION: /email_service.py
# FIXES: Support both SMTP and Brevo HTTP modes via USE_SMTP flag

import threading
import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import url_for, current_app
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class EmailService:
    """Handles all email operations - supports SMTP and Brevo HTTP modes"""
    
    # Mode selection (set USE_SMTP=true in .env to use SMTP, otherwise Brevo HTTP)
    USE_SMTP = os.environ.get('USE_SMTP', 'false').lower() == 'true'
    
    # SMTP Configuration (original)
    SMTP_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('MAIL_PORT', 587))
    SMTP_USERNAME = os.environ.get('MAIL_USERNAME', 'scholarsubmit1@gmail.com').strip()
    SMTP_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    
    # Brevo HTTP Configuration
    BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '').strip()
    BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
    
    # Common configuration
    SENDER_EMAIL = os.environ.get('MAIL_USERNAME', '').strip()
    SENDER_NAME = os.environ.get('MAIL_SENDER_NAME', 'Submita')
    
    @classmethod
    def is_configured(cls):
        """Check if email service is properly configured based on selected mode"""
        if cls.USE_SMTP:
            return bool(cls.SMTP_USERNAME and cls.SMTP_PASSWORD)
        else:
            return bool(cls.BREVO_API_KEY and cls.SENDER_EMAIL)
    
    @classmethod
    def get_mode(cls):
        """Return current email mode as string"""
        return "SMTP" if cls.USE_SMTP else "Brevo HTTP"
    
    @staticmethod
    def send_email_async(recipient, subject, html_content, text_content=None):
        """Send email asynchronously using selected method"""
        
        # Check configuration
        if not EmailService.is_configured():
            print(f"❌ Email not sent - Missing configuration for {EmailService.get_mode()} mode")
            print(f"   USE_SMTP: {EmailService.USE_SMTP}")
            if EmailService.USE_SMTP:
                print(f"   SMTP_USERNAME: {'✅' if EmailService.SMTP_USERNAME else '❌'}")
                print(f"   SMTP_PASSWORD: {'✅' if EmailService.SMTP_PASSWORD else '❌'}")
            else:
                print(f"   BREVO_API_KEY: {'✅' if EmailService.BREVO_API_KEY else '❌'}")
                print(f"   MAIL_USERNAME: {'✅' if EmailService.SENDER_EMAIL else '❌'}")
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
        """Send email using selected method"""
        
        def execute_send():
            if EmailService.USE_SMTP:
                EmailService._send_smtp(recipient, subject, html_content, text_content)
            else:
                EmailService._send_brevo(recipient, subject, html_content, text_content)
        
        if app_context:
            with app_context.app_context():
                execute_send()
        else:
            execute_send()
    
    @staticmethod
    def _send_smtp(recipient, subject, html_content, text_content):
        """Send email using traditional SMTP"""
        try:
            if not EmailService.SMTP_PASSWORD:
                print(f"Cannot send email: SMTP password not configured")
                return
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{EmailService.SENDER_NAME} <{EmailService.SMTP_USERNAME}>"
            msg['To'] = recipient
            
            if text_content:
                part_text = MIMEText(text_content, 'plain')
                msg.attach(part_text)
            
            part_html = MIMEText(html_content, 'html')
            msg.attach(part_html)
            
            with smtplib.SMTP(EmailService.SMTP_SERVER, EmailService.SMTP_PORT) as server:
                server.starttls()
                server.login(EmailService.SMTP_USERNAME, EmailService.SMTP_PASSWORD)
                server.send_message(msg)
                print(f"✅ SMTP email sent to {recipient}")
                
        except Exception as e:
            print(f"❌ SMTP email failed for {recipient}: {e}")
    
    @staticmethod
    def _send_brevo(recipient, subject, html_content, text_content):
        """Send email using Brevo HTTP API"""
        try:
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": EmailService.BREVO_API_KEY
            }
            
            payload = {
                "sender": {
                    "name": EmailService.SENDER_NAME,
                    "email": EmailService.SENDER_EMAIL
                },
                "to": [{"email": recipient}],
                "subject": subject,
                "htmlContent": html_content
            }
            
            if text_content:
                payload["textContent"] = text_content
            
            response = requests.post(
                EmailService.BREVO_API_URL, 
                json=payload, 
                headers=headers, 
                timeout=30
            )
            
            if response.status_code in [200, 201, 202]:
                data = response.json()
                print(f"✅ Brevo email sent to {recipient}! Message ID: {data.get('messageId', 'unknown')}")
            else:
                print(f"❌ Brevo failed for {recipient}: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"❌ Brevo timeout for {recipient}")
        except Exception as e:
            print(f"❌ Brevo error for {recipient}: {str(e)}")
    
    # ==================== EMAIL TEMPLATES ====================
    
    @staticmethod
    def send_verification_email(user_name, user_email, student_id, verification_code):
        """Send account verification email"""
        try:
            base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
            verification_link = f"{base_url}/verify"
        except:
            verification_link = url_for('verify', _external=True)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #059669, #047857); padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .header h1 {{ color: #fff; margin: 0; }}
                .content {{ padding: 30px; background: #fff; border: 1px solid #e5e7eb; border-radius: 0 0 10px 10px; }}
                .code {{ background: #f0fdf4; border: 2px dashed #059669; border-radius: 10px; padding: 20px; text-align: center; margin: 20px 0; }}
                .code-value {{ font-size: 32px; font-weight: bold; color: #047857; letter-spacing: 5px; }}
                .student-id {{ background: #f9fafb; padding: 15px; text-align: center; border-radius: 8px; margin: 15px 0; }}
                .button {{ display: inline-block; background: #059669; color: #fff; padding: 12px 30px; text-decoration: none; border-radius: 8px; margin-top: 20px; }}
                .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Submita!</h1>
                </div>
                <div class="content">
                    <p>Hello <strong>{user_name}</strong>,</p>
                    <p>Thank you for creating an account with Submita. Please use the verification code below to activate your account:</p>
                    
                    <div class="code">
                        <p style="margin-bottom: 10px;">Your Verification Code</p>
                        <div class="code-value">{verification_code}</div>
                        <p style="margin-top: 10px; font-size: 12px;">This code expires in 24 hours</p>
                    </div>
                    
                    <div class="student-id">
                        <p><strong>Your Student ID:</strong> {student_id}</p>
                        <p style="font-size: 12px; margin-top: 5px;">Keep this ID for future logins</p>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{verification_link}" class="button">Verify Your Account</a>
                    </div>
                    
                    <p style="margin-top: 20px;">Or enter the code manually on the verification page.</p>
                    <p>If you didn't create this account, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Submita. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Submita!
        
        Hello {user_name},
        
        Your verification code is: {verification_code}
        Your Student ID is: {student_id}
        
        Verify your account at: {verification_link}
        
        This code expires in 24 hours.
        
        © 2026 Submita
        """
        
        return EmailService.send_email_async(user_email, "Verify Your Submita Account", html_content, text_content)
    
    @staticmethod
    def send_lecturer_verification_email(lecturer_data, verification_code, expires_at):
        """Send lecturer verification code email"""
        try:
            base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
            registration_link = f"{base_url}/register"
        except:
            registration_link = url_for('register', _external=True)
        
        if len(verification_code) > 6:
            formatted_code = ' '.join([verification_code[i:i+3] for i in range(0, len(verification_code), 3)])
        else:
            formatted_code = verification_code
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 550px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #059669, #047857); padding: 25px; text-align: center; color: white; }}
                .code-box {{ background: #f0fdf4; border: 3px solid #059669; border-radius: 12px; padding: 25px; text-align: center; margin: 20px 0; }}
                .code {{ font-size: 36px; font-weight: bold; color: #047857; font-family: monospace; }}
                .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; }}
                .button {{ background: #059669; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; display: inline-block; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Lecturer Verification Code</h1>
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
                        <strong>⚠️ Security Notice:</strong>
                        <p>• This code expires on <strong>{expires_at.strftime('%Y-%m-%d at %H:%M')}</strong></p>
                        <p>• This code can only be used once</p>
                        <p>• Never share this code with anyone</p>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{registration_link}" class="button">Complete Registration →</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email_async(lecturer_data['email'], "🔐 Submita Lecturer Verification Code", html_content)
    
    @staticmethod
    def send_password_reset_email(user_email, reset_token):
        """Send password reset email"""
        try:
            base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
            reset_link = f"{base_url}/reset-password?token={reset_token}"
        except:
            reset_link = url_for('reset_password', token=reset_token, _external=True)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #059669; padding: 20px; text-align: center; color: white; }}
                .button {{ background: #059669; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; display: inline-block; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Password Reset Request</h2>
                </div>
                <div class="content">
                    <p>Click the button below to reset your password:</p>
                    <div style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </div>
                    <p>This link expires in 1 hour.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email_async(user_email, "Reset Your Submita Password", html_content)
    
    @staticmethod
    def send_grade_notification(student_email, student_name, assignment_title, grade, feedback=None):
        """Send grade notification email"""
        try:
            base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
            dashboard_link = f"{base_url}/student-dashboard"
        except:
            dashboard_link = url_for('student_dashboard', _external=True)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #059669, #047857); padding: 20px; text-align: center; color: white; }}
                .grade {{ font-size: 48px; font-weight: bold; color: #059669; text-align: center; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Assignment Graded!</h2>
                </div>
                <div class="content">
                    <p>Hello <strong>{student_name}</strong>,</p>
                    <p>Your assignment "<strong>{assignment_title}</strong>" has been graded.</p>
                    <div class="grade">{grade}%</div>
                    {f'<p><strong>Feedback:</strong><br>{feedback}</p>' if feedback else ''}
                    <p><a href="{dashboard_link}">View on Dashboard →</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email_async(student_email, f"Grade Posted: {assignment_title}", html_content)


# Test function
if __name__ == '__main__':
    print("=" * 60)
    print("📧 EMAIL SERVICE TEST")
    print("=" * 60)
    print(f"Mode: {EmailService.get_mode()}")
    print(f"Configured: {EmailService.is_configured()}")
    print(f"Sender Email: {EmailService.SENDER_EMAIL if EmailService.SENDER_EMAIL else '❌'}")
    
    if EmailService.USE_SMTP:
        print(f"SMTP Server: {EmailService.SMTP_SERVER}:{EmailService.SMTP_PORT}")
    else:
        print(f"Brevo API: {'✅' if EmailService.BREVO_API_KEY else '❌'}")