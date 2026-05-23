# FILE: email_service.py
# LOCATION: /email_service.py
# FIXES: Switched to standard port 465 SSL compatibility, optimized context state handling, fixed inline f-string evaluations

import threading
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import url_for, current_app
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmailService:
    """Handles all email operations asynchronously"""
    
    # Email configuration from environment variables
    SMTP_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('MAIL_PORT', 465)) # Default to 465 (SSL) for production stability
    SENDER_EMAIL = os.environ.get('MAIL_USERNAME', 'scholarsubmit1@gmail.com')
    SENDER_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    
    @staticmethod
    def send_email_async(recipient, subject, html_content, text_content=None):
        """Send email in background thread safely maintaining Flask application state"""
        if not EmailService.SENDER_PASSWORD:
            print(f"Email not sent - SMTP password not configured. To: {recipient}, Subject: {subject}")
            return False
            
        # Capture the current application context so Flask doesn't drop it across threads
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
        """Actual email sending function using secure SMTP network protocols"""
        
        def execute_send():
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = f"Submita <{EmailService.SENDER_EMAIL}>"
                msg['To'] = recipient
                
                if text_content:
                    part_text = MIMEText(text_content, 'plain')
                    msg.attach(part_text)
                
                part_html = MIMEText(html_content, 'html')
                msg.attach(part_html)
                
                # Use SMTP_SSL for Port 465 - sets up immediate implicit encryption
                if EmailService.SMTP_PORT == 465:
                    with smtplib.SMTP_SSL(EmailService.SMTP_SERVER, EmailService.SMTP_PORT, timeout=15) as server:
                        server.login(EmailService.SENDER_EMAIL, EmailService.SENDER_PASSWORD)
                        server.send_message(msg)
                else:
                    # Fallback configuration for explicit TLS (Port 587)
                    with smtplib.SMTP(EmailService.SMTP_SERVER, EmailService.SMTP_PORT, timeout=15) as server:
                        server.starttls()
                        server.login(EmailService.SENDER_EMAIL, EmailService.SENDER_PASSWORD)
                        server.send_message(msg)
                        
                print(f"✅ Email sent successfully to {recipient}")
                    
            except Exception as e:
                print(f"❌ Email failed for {recipient}: {e}")

        # Execute inside Flask context wrapper if context exists
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
                        <a href="{verification_link}" class="button" style="color: white;">Verify Your Account</a>
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
        
        if len(verification_code) > 6:
            formatted_code = ' '.join([verification_code[i:i+3] for i in range(0, len(verification_code), 3)])
        else:
            formatted_code = verification_code
            
        # Clean up code class calculation prior to multi-line evaluation
        code_css_class = "code code-small" if len(verification_code) > 8 else "code"
        
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
                        <div class="{code_css_class}">{formatted_code}</div>
                        <p style="margin-top: 15px; font-size: 12px; color: #059669;">🔑 {len(verification_code)}-character code</p>
                    </div>
                    
                    <div class="info">
                        <p><strong>📝 How to use:</strong></p>
                        <p style="margin: 5px 0 0 20px;">1. Copy the code above (case-sensitive)</p>
                        <p style="margin: 5px 0 0 20px;">2. Enter it in the verification field during registration</p>
                    </div>
                    
                    <div class="warning">
                        <p><strong>⚠️ Security Notice:</strong></p>
                        <p>• Code expires on <strong>{expires_at.strftime('%Y-%m-%d at %H:%M')}</strong></p>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{registration_link}" class="button" style="color: white;">Complete Registration →</a>
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
        Expires: {expires_at.strftime('%Y-%m-%d %H:%M')}
        
        Complete your registration at: {registration_link}
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
                        <a href="{reset_link}" class="button" style="color: white;">Reset Password</a>
                    </div>
                    <p>This link expires in 1 hour.</p>
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