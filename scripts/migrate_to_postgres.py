# FILE: migrate_to_postgres.py
# LOCATION: /migrate_to_postgres.py
# FIXED: Proper data type conversion between SQLite and PostgreSQL

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

load_dotenv()

def convert_value(value, column_name=None):
    """Convert SQLite values to PostgreSQL compatible values"""
    
    # Handle None
    if value is None:
        return None
    
    # Convert boolean (SQLite uses 0/1, PostgreSQL uses True/False)
    if isinstance(value, int) and value in (0, 1):
        # Check if this might be a boolean column (heuristic)
        if column_name and any(term in column_name.lower() for term in ['is_', 'verified', 'active', 'used', 'graded', 'locked', 'published', 'draft', 'late', 'auto']):
            return bool(value)
        return value
    
    # Convert datetime objects to string
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    
    # Convert bytes to string if needed
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except:
            return str(value)
    
    return value

def migrate_data():
    """Migrate ALL data from SQLite to PostgreSQL"""
    
    print("\n" + "=" * 60)
    print("🔄 MIGRATING DATA FROM SQLITE TO POSTGRESQL")
    print("=" * 60)
    
    # Find SQLite database
    possible_paths = [
        'instance/submita.db',
        os.path.join(os.getcwd(), 'submita.db'),
        os.path.join(os.getcwd(), 'instance', 'submita.db'),
    ]
    
    sqlite_path = None
    for path in possible_paths:
        if os.path.exists(path):
            sqlite_path = path
            break
    
    if not sqlite_path:
        print("❌ SQLite database not found!")
        return
    
    print(f"\n✅ SQLite database found at: {sqlite_path}")
    print(f"   Size: {os.path.getsize(sqlite_path)} bytes")
    
    # Get PostgreSQL connection
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set in .env file")
        return
    
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    print(f"\n📦 Source: SQLite ({sqlite_path})")
    print(f"🎯 Target: PostgreSQL")
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    print("✅ Connected to SQLite")
    
    # Get tables from SQLite
    sqlite_cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tables = [row[0] for row in sqlite_cursor.fetchall()]
    
    print(f"\n📋 Found {len(tables)} tables in SQLite:")
    for table in tables:
        sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = sqlite_cursor.fetchone()[0]
        print(f"   - {table}: {count} rows")
    
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(database_url)
    pg_cursor = pg_conn.cursor()
    print("\n✅ Connected to PostgreSQL")
    
    # Disable triggers and foreign key checks
    pg_cursor.execute("SET session_replication_role = 'replica';")
    print("⚠️ Foreign key checks disabled")
    
    migrated_count = 0
    table_counts = {}
    
    # Migrate tables in correct order (users first, then dependent tables)
    migration_order = ['users', 'colleges', 'departments', 'courses', 'semesters', 
                       'assignments', 'submissions', 'student_enrollments', 
                       'activity_logs', 'verification_codes', 'lecturer_verifications',
                       'lecturer_registration_requests']
    
    for table in migration_order:
        if table not in tables:
            continue
            
        try:
            print(f"\n📋 Migrating {table}...")
            
            # Get data from SQLite
            sqlite_cursor.execute(f"SELECT * FROM {table}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print(f"   No data in {table}")
                continue
            
            # Get column names and create placeholder
            columns = [description[0] for description in sqlite_cursor.description]
            placeholders = ','.join(['%s'] * len(columns))
            columns_str = ','.join(columns)
            
            # Clear existing data
            pg_cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
            print(f"   Cleared existing data")
            
            # Convert and insert each row
            inserted = 0
            for row in rows:
                try:
                    # Convert values
                    converted_row = []
                    for col in columns:
                        value = row[col]
                        # Special handling for boolean columns
                        if isinstance(value, int) and value in (0, 1):
                            # Check column name patterns
                            if any(term in col.lower() for term in ['is_', 'verified', 'active', 'used', 'graded', 'locked', 'published', 'draft', 'late', 'auto', 'email_verified', 'account_active']):
                                value = bool(value)
                        # Handle datetime
                        elif hasattr(value, 'isoformat'):
                            value = value.isoformat()
                        converted_row.append(value)
                    
                    # Insert
                    pg_cursor.execute(f"""
                        INSERT INTO {table} ({columns_str}) 
                        VALUES ({placeholders})
                    """, converted_row)
                    inserted += 1
                    
                except Exception as row_error:
                    print(f"   Failed to insert row: {row_error}")
                    continue
            
            pg_conn.commit()
            print(f"   ✅ Migrated {inserted} rows")
            migrated_count += inserted
            table_counts[table] = inserted
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            pg_conn.rollback()
    
    # Re-enable triggers
    pg_cursor.execute("SET session_replication_role = 'origin';")
    print("\n✅ Foreign key checks re-enabled")
    
    sqlite_conn.close()
    pg_cursor.close()
    pg_conn.close()
    
    print("\n" + "=" * 60)
    print("📊 MIGRATION SUMMARY")
    print("=" * 60)
    for table, count in table_counts.items():
        print(f"   {table}: {count} rows")
    print("-" * 60)
    print(f"   TOTAL: {migrated_count} rows")
    print("=" * 60)
    
    if migrated_count > 0:
        print("\n🎉 Migration completed successfully!")
    else:
        print("\n⚠️ No data was migrated.")

if __name__ == '__main__':
    migrate_data()