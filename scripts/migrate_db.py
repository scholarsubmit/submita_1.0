import sqlite3

def add_columns():
    conn = sqlite3.connect('submita.db')
    cursor = conn.cursor()
    
    # Check if columns exist and add them if they don't
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'is_active' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
        print("✅ Added is_active column")
    
    if 'is_authenticated' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_authenticated BOOLEAN DEFAULT 1")
        print("✅ Added is_authenticated column")
    
    if 'is_anonymous' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_anonymous BOOLEAN DEFAULT 0")
        print("✅ Added is_anonymous column")
    
    conn.commit()
    conn.close()
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    add_columns()