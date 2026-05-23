# FILE: test_remote_db.py
# LOCATION: /test_remote_db.py
# PURPOSE: Test connection to remote PostgreSQL

import os
from dotenv import load_dotenv
import psycopg2
import time

load_dotenv()

def test_remote_connection():
    """Test connection to remote PostgreSQL database"""
    
    print("\n" + "=" * 60)
    print("TESTING REMOTE POSTGRESQL CONNECTION")
    print("=" * 60)
    
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL not found in .env file")
        print("\nPlease add DATABASE_URL to your .env file")
        return False
    
    # Hide password for display
    display_url = database_url
    if '@' in database_url:
        parts = database_url.split('@')
        if ':' in parts[0]:
            user_pass = parts[0].split('://')[1] if '://' in parts[0] else parts[0]
            if ':' in user_pass:
                hidden = user_pass.split(':')[0] + ':****'
                display_url = database_url.replace(user_pass, hidden)
    
    print(f"\n📡 Attempting to connect to: {display_url}")
    
    try:
        # Test connection with timeout
        start_time = time.time()
        
        conn = psycopg2.connect(
            database_url,
            connect_timeout=10
        )
        
        elapsed = time.time() - start_time
        
        print(f"✅ Connected successfully in {elapsed:.2f} seconds!")
        
        # Get database info
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"📦 PostgreSQL Version: {version[:50]}...")
        
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]
        print(f"🗄️  Database Name: {db_name}")
        
        cursor.execute("SELECT current_user;")
        db_user = cursor.fetchone()[0]
        print(f"👤 Database User: {db_user}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Remote PostgreSQL is ready!")
        print("=" * 60)
        return True
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nPossible issues:")
        print("  1. Check your DATABASE_URL in .env file")
        print("  2. Make sure your IP is whitelisted in remote database settings")
        print("  3. Check if database server is running")
        print("  4. Verify network/firewall settings")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == '__main__':
    test_remote_connection()