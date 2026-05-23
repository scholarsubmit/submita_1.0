# FILE: db_monitor.py
# LOCATION: /db_monitor.py
# PURPOSE: Monitor remote database connection health

from app import app, db
from sqlalchemy import text
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_db_connection():
    """Check if database connection is alive"""
    try:
        with app.app_context():
            db.session.execute(text('SELECT 1'))
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def get_db_connection_info():
    """Get database connection information"""
    try:
        with app.app_context():
            result = db.session.execute(text("""
                SELECT 
                    current_database() as database_name,
                    current_user as user,
                    inet_server_addr() as server_address,
                    version() as version
            """))
            row = result.fetchone()
            return {
                'database': row[0],
                'user': row[1],
                'server': row[2],
                'version': row[3][:50]
            }
    except Exception as e:
        logger.error(f"Failed to get connection info: {e}")
        return None

if __name__ == '__main__':
    print("\nChecking remote database connection...")
    if check_db_connection():
        print("✅ Database connection is active")
        info = get_db_connection_info()
        if info:
            print(f"📊 Database: {info['database']}")
            print(f"👤 User: {info['user']}")
            print(f"🌐 Server: {info['server']}")
            print(f"📦 Version: {info['version']}")
    else:
        print("❌ Database connection failed")