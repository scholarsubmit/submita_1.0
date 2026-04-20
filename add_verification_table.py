import sqlite3
import os

# Path to your database
db_path = 'instance/submita.db'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create verification_code table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verification_code (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            assignment_id INTEGER NOT NULL,
            code VARCHAR(10) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL,
            is_used BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES user (id),
            FOREIGN KEY (assignment_id) REFERENCES assignment_submission (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ VerificationCode table created successfully!")
else:
    print(f"Database not found at {db_path}")