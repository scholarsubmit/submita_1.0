"""
app/utils/security.py — validation and sanitization helpers shared by
every auth route. Keeping these centralized means a policy change (e.g.
matric format, password rules) happens in exactly one place.
"""
import html
import re
from flask import current_app


# ==================== MATRIC NUMBER ====================
def validate_matric_format(matric):
    """
    Validates against Config.MATRIC_REGEX, e.g. MOUAU/CSC/22/012345.
    Returns (is_valid, error_message).
    """
    if not matric:
        return False, 'Matric number is required.'
    pattern = current_app.config['MATRIC_REGEX']
    if not re.match(pattern, matric.strip().upper()):
        example = current_app.config['MATRIC_EXAMPLE']
        return False, f'Matric number must look like {example}.'
    return True, None


def normalize_matric(matric):
    return matric.strip().upper() if matric else matric


# ==================== PASSWORD STRENGTH ====================
COMMON_PASSWORDS = {
    'password123', 'password1234', 'admin1234', 'qwerty1234',
    'welcome1234', 'student123', 'lecturer123', 'submita123',
}


def validate_password_strength(password):
    """Returns (is_valid, list_of_error_messages)."""
    errors = []
    min_len = current_app.config.get('PASSWORD_MIN_LENGTH', 10)

    if len(password) < min_len:
        errors.append(f'Password must be at least {min_len} characters long.')
    if len(password) > 128:
        errors.append('Password must be under 128 characters.')
    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain an uppercase letter.')
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain a lowercase letter.')
    if not re.search(r'\d', password):
        errors.append('Password must contain a number.')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-\[\]]', password):
        errors.append('Password must contain a special character.')
    if password.lower() in COMMON_PASSWORDS:
        errors.append('That password is too common. Please choose something more unique.')

    return len(errors) == 0, errors


# ==================== INPUT SANITIZATION ====================
_SQL_KEYWORD_PATTERN = re.compile(
    r'(?i)\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b'
)
_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def sanitize_input(value):
    """Strip control chars, HTML-escape, and neutralize obvious SQLi keywords.
    Note: parameterized queries (via SQLAlchemy) are the REAL SQL-injection
    defense — this is a defense-in-depth layer on top, not a substitute."""
    if isinstance(value, str):
        value = _CONTROL_CHARS.sub('', value)
        value = html.escape(value)
        return value.strip()
    if isinstance(value, dict):
        return {k: sanitize_input(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_input(v) for v in value]
    return value


def valid_email_format(email):
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email or ''))
