# FILE: email_service.py
# LOCATION: /email_service.py
# FIXES: Replace SMTP with Brevo HTTP REST API

import threading
import os
import requests
from flask import url_for, current_app
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class EmailService:
    """Handles all email operations asynchronously using Brevo REST API"""
    
    # Brevo API Configuration
    BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
    API_KEY = os.environ.get('BREVO_API_KEY', '')
    
    # Sender information - can be configured via environment
    SENDER_NAME = os.environ.get('MAIL_SENDER_NAME', 'Submita')
    SENDER_EMAIL = os.environ.get('MAIL_USERNAME', '')
    
    @staticmethod
    def send_email_async(recipient, subject, html_content, text_content=None):
        """Send email via background thread to prevent blocking the Flask UI"""
        if not EmailService.API_KEY:
            print(f"❌ Email aborted - BREVO_API_KEY missing from environment.")
            print("   Please add BREVO_API_KEY to your .env file")
            return False
        
        if not EmailService.SENDER_EMAIL:
            print(f"❌ Email aborted - MAIL_USERNAME (sender email) missing from environment.")
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
        """Execute the Brevo HTTP API call"""
        
        def execute_send():
            # Build headers required by Brevo's REST API
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": EmailService.API_KEY
            }
            
            # Build Brevo's required payload
            payload = {
                "sender": {
                    "name": EmailService.SENDER_NAME,
                    "email": EmailService.SENDER_EMAIL
                },
                "to": [{"email": recipient, "name": recipient.split('@')[0]}],
                "subject": subject,
                "htmlContent": html_content
            }
            
            # Add plain text version if provided
            if text_content:
                payload["textContent"] = text_content
            
            try:
                # Make the API call
                response = requests.post(
                    EmailService.BREVO_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code in [200, 201, 202]:
                    response_data = response.json()
                    message_id = response_data.get('messageId', 'unknown')
                    print(f"✅ Email sent successfully to {recipient}! Message ID: {message_id}")
                else:
                    print(f"❌ Brevo API Error {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                print(f"❌ Brevo API timeout for {recipient}")
            except requests.exceptions.ConnectionError:
                print(f"❌ Brevo API connection error for {recipient}")
            except Exception as e:
                print(f"❌ Brevo API exception for {recipient}: {str(e)}")
        
        if app_context:
            with app_context.app_context():
                execute_send()
        else:
            execute_send()
    
    @staticmethod
    def send_verification_email(user_name, user_email, student_id, verification_code):
        """Send account verification email"""
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
                    <p>Your trusted assignment management platform</p>
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
        
        EmailService.send_email_async(user_email, "Verify Your Submita Account", html_content, text_content)
    
    @staticmethod
    def send_lecturer_verification_email(lecturer_data, verification_code, expires_at):
        """Send lecturer verification code email with secure short code"""
        registration_link = url_for('register', _external=True)
        
        # Format the code for display - add spaces every 3 characters for readability
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
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 550px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #059669, #047857); padding: 25px; text-align: center; border-radius: 10px 10px 0 0; }}
                .header h1 {{ color: #fff; margin: 0; font-size: 22px; }}
                .content {{ padding: 30px; background: #fff; border: 1px solid #e5e7eb; border-radius: 0 0 10px 10px; }}
                .code-box {{ background: #f0fdf4; border: 3px solid #059669; border-radius: 12px; padding: 25px; text-align: center; margin: 20px 0; }}
                .code {{ font-size: 36px; font-weight: bold; color: #047857; font-family: 'Courier New', monospace; letter-spacing: 5px; }}
                .code-small {{ font-size: 28px; }}
                .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 8px; }}
                .info {{ background: #e0f2fe; border-left: 4px solid #0284c7; padding: 15px; margin: 20px 0; border-radius: 8px; }}
                .button {{ display: inline-block; background: #059669; color: #fff; padding: 12px 25px; text-decoration: none; border-radius: 8px; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Lecturer Verification Code</h1>
                </div>
                <div class="content">
                    <p>Dear <strong>{lecturer_data['full_name']}</strong>,</p>
                    <p>You have been invited to join Submita as a lecturer. Use the verification code below to complete your registration:</p>
                    
                    <div class="code-box">
                        <p style="margin-bottom: 10px; font-size: 14px;">Your Secure Verification Code</p>
                        <div class="code {'code-small' if len(verification_code) > 8 else ''}">{formatted_code}</div>
                        <p style="margin-top: 15px; font-size: 12px; color: #059669;">
                            🔑 {len(verification_code)}-character code
                        </p>
                    </div>
                    
                    <div class="info">
                        <p><strong>📝 How to use:</strong></p>
                        <p style="margin: 5px 0 0 20px;">1. Copy the code above (case-sensitive)</p>
                        <p style="margin: 5px 0 0 20px;">2. Enter it in the verification field during registration</p>
                        <p style="margin: 5px 0 0 20px;">3. Complete your profile setup</p>
                    </div>
                    
                    <div class="warning">
                        <p><strong>⚠️ Security Notice:</strong></p>
                        <p>• This code can only be used <strong>once</strong></p>
                        <p>• Never share this code with anyone</p>
                        <p>• Code expires on <strong>{expires_at.strftime('%Y-%m-%d at %H:%M')}</strong></p>
                        <p>• Submita will never ask for this code outside registration</p>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{registration_link}" class="button">Complete Registration →</a>
                    </div>
                    
                    <div class="footer">
                        <p>If you did not request this verification, please ignore this email or contact support immediately.</p>
                        <p>© 2026 Submita - Secure Assignment Platform</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        🔐 Lecturer Verification Code
        
        Dear {lecturer_data['full_name']},
        
        Your secure verification code is: {verification_code}
        Staff ID: {lecturer_data['staff_id']}
        Expires: {expires_at.strftime('%Y-%m-%d %H:%M')}
        
        Complete your registration at: {registration_link}
        
        This {len(verification_code)}-character code can only be used once.
        
        ⚠️ Security Notice:
        - Never share this code with anyone
        - Submita will never ask for this code outside registration
        
        © 2026 Submita
        """
        
        EmailService.send_email_async(lecturer_data['email'], "🔐 Submita Lecturer Verification Code", html_content, text_content)
    
    @staticmethod
    def send_password_reset_email(user_email, reset_token):
        """Send password reset email"""
        reset_link = url_for('reset_password', token=reset_token, _external=True)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #059669; padding: 20px; text-align: center; color: white; border-radius: 10px 10px 0 0; }}
                .content {{ padding: 30px; border: 1px solid #e5e7eb; border-radius: 0 0 10px 10px; }}
                .button {{ background: #059669; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; display: inline-block; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Password Reset Request</h2>
                </div>
                <div class="content">
                    <p>You requested to reset your password. Click the button below to proceed:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </div>
                    <p>This link expires in 1 hour.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        EmailService.send_email_async(user_email, "Reset Your Submita Password", html_content)
    
    @staticmethod
    def send_grade_notification(student_email, student_name, assignment_title, grade, feedback=None):
        """Send grade notification email"""
        dashboard_link = url_for('student_dashboard', _external=True)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #059669, #047857); padding: 20px; text-align: center; color: white; border-radius: 10px 10px 0 0; }}
                .content {{ padding: 30px; border: 1px solid #e5e7eb; border-radius: 0 0 10px 10px; }}
                .grade {{ font-size: 36px; font-weight: bold; color: #059669; text-align: center; margin: 20px 0; }}
                .feedback {{ background: #f9fafb; padding: 15px; border-radius: 8px; margin: 15px 0; }}
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
                    {f'<div class="feedback"><strong>Feedback:</strong><br>{feedback}</div>' if feedback else ''}
                    <div style="text-align: center; margin-top: 20px;">
                        <a href="{dashboard_link}" style="color: #059669;">View on Dashboard →</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        EmailService.send_email_async(student_email, f"Grade Posted: {assignment_title}", html_content)