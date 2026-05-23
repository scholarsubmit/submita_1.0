# utils/email_sender.py
from flask_mail import Message
from flask import current_app, url_for
import os
from datetime import datetime

def send_verification_email(lecturer_data, verification_code, expires_at, pdf_path):
    """
    Send verification email with PDF attachment to lecturer
    """
    try:
        from app import mail
        
        registration_link = f"http://localhost:5000/register?code={verification_code}"
        
        # Professional HTML Email Template
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Lecturer Verification - Submita</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f4f7f6;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                    color: white;
                    padding: 40px 30px;
                    text-align: center;
                }}
                .logo {{
                    font-size: 32px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
                .logo-icon {{
                    font-size: 48px;
                    margin-bottom: 10px;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .greeting {{
                    font-size: 24px;
                    font-weight: 600;
                    color: #1f2937;
                    margin-bottom: 20px;
                }}
                .code-box {{
                    background: #f0fdf4;
                    border: 2px solid #10b981;
                    border-radius: 12px;
                    padding: 25px;
                    text-align: center;
                    margin: 25px 0;
                }}
                .code-label {{
                    font-size: 14px;
                    color: #059669;
                    font-weight: 600;
                    margin-bottom: 10px;
                }}
                .code-value {{
                    font-size: 36px;
                    font-weight: bold;
                    color: #059669;
                    letter-spacing: 3px;
                    font-family: 'Courier New', monospace;
                }}
                .info-grid {{
                    background: #f9fafb;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                }}
                .info-row {{
                    display: flex;
                    padding: 8px 0;
                    border-bottom: 1px solid #e5e7eb;
                }}
                .info-label {{
                    font-weight: 600;
                    width: 120px;
                    color: #4b5563;
                }}
                .info-value {{
                    color: #1f2937;
                }}
                .warning-box {{
                    background: #fef3c7;
                    border-left: 4px solid #f59e0b;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .button {{
                    display: inline-block;
                    background: #10b981;
                    color: white;
                    text-decoration: none;
                    padding: 12px 30px;
                    border-radius: 8px;
                    font-weight: 600;
                    margin: 20px 0;
                    transition: background 0.3s;
                }}
                .button:hover {{
                    background: #059669;
                }}
                .footer {{
                    background: #f9fafb;
                    padding: 20px;
                    text-align: center;
                    font-size: 12px;
                    color: #6b7280;
                    border-top: 1px solid #e5e7eb;
                }}
                .expiry-badge {{
                    background: #fee2e2;
                    color: #991b1b;
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-size: 13px;
                    display: inline-block;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo-icon">📚</div>
                    <div class="logo">Submita</div>
                    <div style="font-size: 14px; margin-top: 10px;">University Assignment Management System</div>
                </div>
                
                <div class="content">
                    <div class="greeting">Dear {lecturer_data['full_name']},</div>
                    
                    <p>We are pleased to inform you that your request to register as a <strong>Lecturer</strong> on the Submita platform has been <strong style="color: #10b981;">approved</strong>.</p>
                    
                    <div class="code-box">
                        <div class="code-label">Your Unique Verification Code</div>
                        <div class="code-value">{verification_code}</div>
                        <div style="font-size: 12px; margin-top: 10px; color: #059669;">Keep this code confidential</div>
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-row">
                            <div class="info-label">Staff ID:</div>
                            <div class="info-value">{lecturer_data['staff_id']}</div>
                        </div>
                        <div class="info-row">
                            <div class="info-label">Department:</div>
                            <div class="info-value">{lecturer_data['department']}</div>
                        </div>
                        <div class="info-row">
                            <div class="info-label">College:</div>
                            <div class="info-value">{lecturer_data.get('college', 'Not specified')}</div>
                        </div>
                    </div>
                    
                    <div class="warning-box">
                        <strong>⏰ Expiration Notice:</strong><br>
                        This verification code will expire on <strong>{expires_at.strftime('%B %d, %Y at %H:%M')}</strong>.<br>
                        Please complete your registration before this date.
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{registration_link}" class="button">🔐 Complete Registration →</a>
                    </div>
                    
                    <div style="margin-top: 25px;">
                        <strong>📋 Important Notes:</strong>
                        <ul style="margin-top: 10px;">
                            <li>This code can only be used once</li>
                            <li>Do not share this code with anyone</li>
                            <li>A PDF copy of this verification is attached to this email</li>
                            <li>After registration, you can start creating assignments immediately</li>
                        </ul>
                    </div>
                </div>
                
                <div class="footer">
                    <p>© 2024 Submita - University Assignment Management System</p>
                    <p style="margin-top: 10px;">This is an automated message. Please do not reply to this email.</p>
                    <p style="margin-top: 5px; font-size: 11px;">
                        <a href="#" style="color: #6b7280;">Privacy Policy</a> | 
                        <a href="#" style="color: #6b7280;">Terms of Service</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version for email clients that don't support HTML
        text_content = f"""
        SUBMITA - LECTURER VERIFICATION CODE
        
        Dear {lecturer_data['full_name']},
        
        Your request to register as a Lecturer has been approved.
        
        VERIFICATION CODE: {verification_code}
        
        Your Details:
        - Staff ID: {lecturer_data['staff_id']}
        - Department: {lecturer_data['department']}
        - College: {lecturer_data.get('college', 'Not specified')}
        
        This code expires on: {expires_at.strftime('%B %d, %Y at %H:%M')}
        
        Register here: {registration_link}
        
        Important:
        - This code can only be used once
        - Keep this code confidential
        - A PDF copy is attached to this email
        
        © 2024 Submita
        """
        
        # Create message
        msg = Message(
            subject=f"🔐 Submita Lecturer Verification Code - {lecturer_data['full_name']}",
            recipients=[lecturer_data['email']],
            html=html_content,
            body=text_content,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        # Attach PDF
        if pdf_path and os.path.exists(pdf_path):
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
        print(f"❌ Email sending error: {str(e)}")
        return False