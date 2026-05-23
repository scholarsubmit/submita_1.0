# FILE: config.py
# LOCATION: /config.py
# FIXES: Handle postgres:// and postgresql:// URLs correctly

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── Security ────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'd9f8c7b6a5e4d3c2b1a0f9e8d7c6b5a4')
    SESSION_PERMANENT = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600

    # ── Database Configuration ──────────────────────────────────────────────
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        # Convert postgres:// to postgresql:// (Heroku style)
        db_url = DATABASE_URL
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
            print(f"📝 Converted URL from postgres:// to postgresql://")
        
        SQLALCHEMY_DATABASE_URI = db_url
        print(f"✅ Using PostgreSQL database")
    else:
        # Fallback to SQLite
        SQLALCHEMY_DATABASE_URI = 'sqlite:///submita.db'
        print(f"📁 Using SQLite database")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Engine options based on database type
    if SQLALCHEMY_DATABASE_URI.startswith('sqlite'):
        SQLALCHEMY_ENGINE_OPTIONS = {
            'connect_args': {'check_same_thread': False, 'timeout': 30}
        }
    else:
        # PostgreSQL options
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': int(os.environ.get('DB_POOL_SIZE', 5)),
            'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 10)),
            'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 30)),
            'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 3600)),
            'pool_pre_ping': True,
        }

    # ── Mail Configuration ──────────────────────────────────────────────────
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'scholarsubmit1@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'Submita <scholarsubmit1@gmail.com>')

    # ── Uploads ─────────────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    UPLOAD_FOLDER = 'uploads'
    ASSIGNMENT_FOLDER = 'uploads/assignments'
    SUBMISSION_FOLDER = 'uploads/submissions'
    STATIC_FOLDER = 'static'
    PDF_FOLDER = 'static/pdfs'

    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'py', 'js', 'java', 'cpp', 'c', 'zip', 'rar',
        'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'jpg', 'jpeg', 'png', 'gif',
    }

    # ── App Settings ────────────────────────────────────────────────────────
    APP_NAME = 'Submita'
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Strict'


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}