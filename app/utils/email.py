"""
app/utils/email.py — outbound email via Gmail SMTP (SSL, port 465).
Sending happens in a background thread so a slow/failed SMTP connection
never blocks the HTTP request that triggered it.
"""
import smtplib
import ssl
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app, render_template


def _send_sync(app, recipient, subject, html_body, text_body=None):
    with app.app_context():
        cfg = app.config
        username = cfg.get('MAIL_USERNAME')
        password = cfg.get('MAIL_PASSWORD')
        sender_name = cfg.get('MAIL_SENDER_NAME', 'Submita')

        print(f"🔍 _send_sync called: recipient={recipient!r}, subject={subject!r}, "
              f"username_set={bool(username)}, password_set={bool(password)}")

        if not username or not password:
            print('❌ Email not sent: MAIL_USERNAME/MAIL_PASSWORD not configured in this app context.')
            app.logger.error('Email not sent: MAIL_USERNAME/MAIL_PASSWORD not configured.')
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f'{sender_name} <{username}>'
        msg['To'] = recipient
        if text_body:
            msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg['MAIL_SERVER'], cfg['MAIL_PORT'], context=context, timeout=15) as server:
                server.login(username, password)
                server.send_message(msg)
            print(f'✅ Email actually sent to {recipient}')
            return True
        except Exception as exc:
            print(f'❌ Email send FAILED to {recipient}: {exc}')
            app.logger.error(f'Email send failed to {recipient}: {exc}')
            return False


def send_email_async(recipient, subject, html_body, text_body=None):
    """Fire-and-forget send. Callers should NOT treat a missing return
    value as failure feedback to the user — for that, use send_email_sync
    (e.g. right after registration, where we want to warn the user if
    sending failed)."""
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=_send_sync, args=(app, recipient, subject, html_body, text_body), daemon=True
    )
    thread.start()


def send_email_sync(recipient, subject, html_body, text_body=None):
    app = current_app._get_current_object()
    return _send_sync(app, recipient, subject, html_body, text_body)


# ==================== TEMPLATED MESSAGES ====================
def send_verification_email(user, plaintext_code):
    html_body = render_template('email/verify_code.html', user=user, code=plaintext_code)
    return send_email_sync(user.email, 'Verify your Submita account', html_body)


def send_lecturer_invite_email(email, full_name, plaintext_code, expires_at):
    html_body = render_template(
        'email/lecturer_invite.html', full_name=full_name, code=plaintext_code, expires_at=expires_at
    )
    return send_email_sync(email, 'Your Submita lecturer invite code', html_body)


def send_account_locked_email(user):
    html_body = render_template('email/account_locked.html', user=user)
    send_email_async(user.email, 'Security alert: your Submita account was temporarily locked', html_body)


def send_password_reset_email(user, reset_link):
    html_body = render_template('email/password_reset.html', user=user, reset_link=reset_link)
    return send_email_sync(user.email, 'Reset your Submita password', html_body)
