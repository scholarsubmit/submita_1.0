# FILE: utils/email_utils.py
# LOCATION: /utils/email_utils.py
# FIXES: Get BASE_URL from environment instead of hardcoding localhost

from flask_mail import Mail, Message
from flask import current_app
from utils.pdf_generator import generate_lecturer_verification_pdf
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

mail = Mail()

def get_base_url():
    """Get BASE_URL from environment or fallback to localhost"""
    base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
    return base_url.rstrip('/')

def send_verification_email_with_pdf(lecturer_data, verification_code, expires_at, pdf_path):
    """
    Send verification code email with PDF attachment
    """
    try:
        # Get BASE_URL from environment
        base_url = get_base_url()
        registration_link = f"{base_url}/register"
        
        # Email subject and body
        subject = f"Submita - Lecturer Verification Code for {lecturer_data['full_name']}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ padding: 30px; background: #f9fafb; }}
                .code {{ background: #f0fdf4; border: 2px dashed #10b981; padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0; }}
                .code-text {{ font-size: 28px; font-weight: bold; color: #10b981; letter-spacing: 3px; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #6b7280; background: #f3f4f6; border-radius: 0 0 10px 10px; }}
                .button {{ background: #10b981; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
                .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎓 Submita Lecturer Verification</h1>
                </div>
                <div class="content">
                    <h2>Dear {lecturer_data['full_name']},</h2>
                    <p>Congratulations! Your request to register as a lecturer on the Submita platform has been <strong>approved</strong>.</p>
                    
                    <div class="code">
                        <p style="margin-bottom: 10px;"><strong>Your Verification Code:</strong></p>
                        <div class="code-text">{verification_code}</div>
                        <p style="margin-top: 10px; font-size: 12px;">Use this code to complete your registration</p>
                    </div>
                    
                    <div class="warning">
                        <strong>⚠️ Important:</strong>
                        <ul style="margin-top: 10px;">
                            <li>This code will expire on: <strong>{expires_at.strftime('%B %d, %Y at %H:%M')}</strong></li>
                            <li>The code can only be used once</li>
                            <li>Keep this code confidential</li>
                        </ul>
                    </div>
                    
                    <h3>How to Register:</h3>
                    <ol>
                        <li>Visit the Submita registration page</li>
                        <li>Select <strong>"Lecturer"</strong> as your role</li>
                        <li>Enter your details and the verification code above</li>
                        <li>Complete the registration form</li>
                        <li>You will be automatically logged in</li>
                    </ol>
                    
                    <div style="text-align: center;">
                        <a href="{registration_link}" class="button">Go to Registration →</a>
                    </div>
                    
                    <hr style="margin: 30px 0;">
                    <p style="font-size: 12px; color: #6b7280;">
                        Attached to this email is a PDF copy of your verification code for your records.<br>
                        Please keep this PDF safe as you will need it for registration.
                    </p>
                </div>
                <div class="footer">
                    <p>This is an automated message from Submita. Please do not reply to this email.</p>
                    <p>&copy; 2024 Submita - University Assignment Management System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create message
        msg = Message(
            subject=subject,
            recipients=[lecturer_data['email']],
            html=html_body,
            sender=current_app.config.get('MAIL_USERNAME', 'noreply@submita.com')
        )
        
        # Attach PDF
        with open(pdf_path, 'rb') as f:
            msg.attach(
                filename=os.path.basename(pdf_path),
                content_type='application/pdf',
                data=f.read()
            )
        
        # Send email
        mail.send(msg)
        return True
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False


def send_student_verification_email(student_email, student_name, verification_code, student_id):
    """
    Send verification email to student
    """
    try:
        base_url = get_base_url()
        verification_link = f"{base_url}/verify?code={verification_code}&email={student_email}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #10b981; padding: 20px; text-align: center; color: white; }}
                .code {{ background: #f0fdf4; border: 2px dashed #10b981; padding: 15px; text-align: center; margin: 20px 0; }}
                .code-text {{ font-size: 24px; font-weight: bold; color: #10b981; letter-spacing: 3px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Welcome to Submita!</h2>
                </div>
                <div class="content">
                    <p>Dear <strong>{student_name}</strong>,</p>
                    <p>Thank you for registering with Submita. Please verify your email address to activate your account.</p>
                    
                    <div class="code">
                        <p><strong>Your Verification Code:</strong></p>
                        <div class="code-text">{verification_code}</div>
                        <p style="font-size: 12px;">Student ID: {student_id}</p>
                    </div>
                    
                    <div style="text-align: center; margin: 20px 0;">
                        <a href="{verification_link}" style="background: #10b981; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email →</a>
                    </div>
                    
                    <p>Or enter the code manually on the verification page.</p>
                    <p>This code expires in 24 hours.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = Message(
            subject="Verify Your Submita Account",
            recipients=[student_email],
            html=html_body,
            sender=current_app.config.get('MAIL_USERNAME', 'noreply@submita.com')
        )
        
        mail.send(msg)
        return True
        
    except Exception as e:
        print(f"Error sending student verification email: {str(e)}")
        return False


def send_grade_notification(student_email, student_name, assignment_title, grade, feedback=None):
    """
    Send grade notification to student
    """
    try:
        base_url = get_base_url()
        dashboard_link = f"{base_url}/student-dashboard"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981, #059669); padding: 20px; text-align: center; color: white; }}
                .grade {{ font-size: 48px; font-weight: bold; color: #10b981; text-align: center; margin: 20px 0; }}
                .feedback {{ background: #f9fafb; padding: 15px; border-radius: 8px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Assignment Graded!</h2>
                </div>
                <div class="content">
                    <p>Dear <strong>{student_name}</strong>,</p>
                    <p>Your assignment "<strong>{assignment_title}</strong>" has been graded.</p>
                    
                    <div class="grade">{grade}%</div>
                    
                    {f'<div class="feedback"><strong>Feedback:</strong><br>{feedback}</div>' if feedback else ''}
                    
                    <div style="text-align: center; margin-top: 20px;">
                        <a href="{dashboard_link}" style="color: #10b981;">View on Dashboard →</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = Message(
            subject=f"Grade Posted: {assignment_title}",
            recipients=[student_email],
            html=html_body,
            sender=current_app.config.get('MAIL_USERNAME', 'noreply@submita.com')
        )
        
        mail.send(msg)
        return True
        
    except Exception as e:
        print(f"Error sending grade notification: {str(e)}")
        return False


def send_password_reset_email(user_email, user_name, reset_token):
    """
    Send password reset email
    """
    try:
        base_url = get_base_url()
        reset_link = f"{base_url}/reset-password?token={reset_token}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #10b981; padding: 20px; text-align: center; color: white; }}
                .button {{ background: #10b981; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Reset Your Password</h2>
                </div>
                <div class="content">
                    <p>Dear <strong>{user_name}</strong>,</p>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_link}" class="button">Reset Password →</a>
                    </div>
                    
                    <p>This link will expire in 1 hour.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = Message(
            subject="Reset Your Submita Password",
            recipients=[user_email],
            html=html_body,
            sender=current_app.config.get('MAIL_USERNAME', 'noreply@submita.com')
        )
        
        mail.send(msg)
        return True
        
    except Exception as e:
        print(f"Error sending password reset email: {str(e)}")
        return False