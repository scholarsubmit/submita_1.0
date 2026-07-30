"""
config.py — central configuration, actually loaded by app/__init__.py via
app.config.from_object(). (In the old project, config.py existed but was
never applied — every setting here is live.)
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _database_uri():
    url = os.environ.get('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    # Force the psycopg3 dialect. Without "+psycopg", SQLAlchemy defaults to
    # the psycopg2 driver, which we no longer install (see requirements.txt).
    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return url or 'sqlite:///submita.db'


class Config:
    # ── Core ─────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        # Fail loudly in production rather than silently rotating keys
        # (a rotating key invalidates every session/flash on each restart).
        if os.environ.get('FLASK_ENV') == 'production':
            raise RuntimeError('SECRET_KEY must be set in production.')
        SECRET_KEY = 'eecfe78b4f55bb3af82fea746943cadd31fa30806b7061bbab65001e0442c270'

    APP_NAME = 'Submita'
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

    # ── Database ─────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = (
        {'connect_args': {'check_same_thread': False, 'timeout': 30}}
        if SQLALCHEMY_DATABASE_URI.startswith('sqlite')
        else {'pool_size': 5, 'max_overflow': 10, 'pool_timeout': 30,
              'pool_recycle': 1800, 'pool_pre_ping': True}
    )

    # ── Sessions / cookies ───────────────────────────────────────────
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    REMEMBER_COOKIE_DURATION = timedelta(days=7)

    # ── Email (Gmail SMTP over SSL, port 465) ───────────────────────
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'scholarsubmit1@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'luxtxnotbllnpcaj')
    MAIL_SENDER_NAME = os.environ.get('MAIL_SENDER_NAME', 'Submita')

    # ── AI grading (Claude API) ──────────────────────────────────────
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    AI_GRADING_MODEL = os.environ.get('AI_GRADING_MODEL', 'claude-sonnet-4-5')

    # ── Academic identity rules ──────────────────────────────────────
    UNIVERSITY_CODE = os.environ.get('UNIVERSITY_CODE', 'MOUAU')
    # MOUAU/CSC/22/012345 — dept(2-5 letters) / admission year(2 digits) / serial(6 digits)
    # Centralized here (not hardcoded in routes) so the format can change in one place.
    MATRIC_REGEX = r'^{uni}\/[A-Z]{{2,5}}\/\d{{2}}\/\d{{6}}$'.format(uni=UNIVERSITY_CODE)
    MATRIC_EXAMPLE = f'{UNIVERSITY_CODE}/CSC/22/012345'

    # ── Security knobs ───────────────────────────────────────────────
    EMAIL_VERIFICATION_GRACE_HOURS = int(os.environ.get('EMAIL_VERIFICATION_GRACE_HOURS', 48))
    LECTURER_INVITE_EXPIRY_DAYS = int(os.environ.get('LECTURER_INVITE_EXPIRY_DAYS', 7))
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    LOGIN_LOCKOUT_MINUTES = int(os.environ.get('LOGIN_LOCKOUT_MINUTES', 15))
    PASSWORD_MIN_LENGTH = 10

    # ── Uploads ──────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'txt', 'zip',
        'py', 'js', 'java', 'cpp', 'c', 'ipynb',
        'jpg', 'jpeg', 'png',
    }


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


CONFIG_MAP = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
