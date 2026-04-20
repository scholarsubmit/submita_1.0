import os


class Config:
    SECRET_KEY = "d9f8c7b6a5e4d3c2b1a0f9e8d7c6b5a4"
    SQLALCHEMY_DATABASE_URI = "sqlite:///submita.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')

    # Email configuration
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = "scholarsubmit1@gmail.com"
    MAIL_PASSWORD = "luxtxnotbllnpcaj"  # App password with spaces
    MAIL_DEFAULT_SENDER = "scholarsubmit1@gmail.com"
