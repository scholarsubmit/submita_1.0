# test_config.py
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 50)
print("TESTING CONFIGURATION")
print("=" * 50)

# Check DATABASE_URL from .env
db_url = os.environ.get('DATABASE_URL', '')
print(f"📋 Raw DATABASE_URL from .env: {db_url[:50] if db_url else 'Not set'}...")

# Test loading config
try:
    from config import Config
    print(f"✅ Config loaded successfully")
    print(f"📁 Database URL: {Config.SQLALCHEMY_DATABASE_URI[:60] if Config.SQLALCHEMY_DATABASE_URI else 'None'}...")
    print(f"🔧 Debug mode: {Config.DEBUG}")
    print(f"🌐 Host: {Config.HOST}")
    print(f"🔌 Port: {Config.PORT}")
except Exception as e:
    print(f"❌ Config error: {e}")

# Test SQLAlchemy import
try:
    from sqlalchemy import create_engine, text
    print("✅ SQLAlchemy imported")
except Exception as e:
    print(f"❌ SQLAlchemy error: {e}")

# Test database connection
db_url = os.environ.get('DATABASE_URL', '')
if db_url:
    # Convert postgres:// to postgresql:// for testing
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
        print(f"📝 Converted URL for testing")
    
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()
            print(f"✅ PostgreSQL connected successfully!")
            print(f"📦 Version: {version[0][:80]}...")
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print(f"   Make sure your credentials are correct and IP is whitelisted")
else:
    print("ℹ️ No DATABASE_URL set, using SQLite")

print("=" * 50)