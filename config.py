import os

class Config:
    SECRET_KEY = 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///submita.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'scholarsubmit1@gmail.com'
    MAIL_PASSWORD = 'luxtxnotbllnpcaj'   # App password with spaces
    MAIL_DEFAULT_SENDER = 'scholarsubmit1@gmail.com'