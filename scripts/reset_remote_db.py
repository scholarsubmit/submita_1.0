# FILE: reset_remote_db.py
# LOCATION: /reset_remote_db.py
# PURPOSE: Reset remote PostgreSQL database

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

load_dotenv()

print("\n" + "=" * 60)
print("🔄 RESETTING REMOTE POSTGRESQL DATABASE")
print("=" * 60)

# Get database URL
db_url = os.environ.get('DATABASE_URL', '')

if not db_url:
    print("❌ DATABASE_URL not found in .env file")
    exit(1)

# Convert postgres:// to postgresql://
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
    print("✅ Converted postgres:// to postgresql://")

print(f"📁 Database: {db_url[:60]}...")

# Create engine without any special options
engine = create_engine(db_url)

try:
    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()
        
        try:
            # Drop all tables in public schema
            print("\n📦 Dropping all tables...")
            
            # Get all table names
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """))
            
            tables = [row[0] for row in result]
            print(f"   Found {len(tables)} tables")
            
            # Drop tables one by one
            for table in tables:
                try:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                    print(f"   ✅ Dropped: {table}")
                except Exception as e:
                    print(f"   ⚠️ Could not drop {table}: {e}")
            
            # Commit the transaction
            trans.commit()
            print("\n✅ All tables dropped successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ Error during drop: {e}")
            raise
            
except Exception as e:
    print(f"\n❌ Connection error: {e}")
    
print("\n" + "=" * 60)
print("✅ Database reset complete!")
print("=" * 60)
print("\nNow run: python scripts/init_db_tables.py")