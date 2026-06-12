# update_db.py
from app import app, db
from sqlalchemy import text

print("=" * 50)
print("UPDATING DATABASE SCHEMA")
print("=" * 50)

with app.app_context():
    # Check current columns
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    existing_columns = [c['name'] for c in inspector.get_columns('users')]
    print(f"\nExisting columns: {existing_columns}")
    
    # List of columns to add if missing
    columns_to_add = [
        ('current_level', 'VARCHAR(10)', "'100'"),
        ('enrollment_year', 'VARCHAR(20)', 'NULL'),
        ('expected_graduation_year', 'VARCHAR(20)', 'NULL'),
        ('program_duration', 'INTEGER', '4'),
        ('academic_standing', 'VARCHAR(20)', "'good'"),
        ('cgpa', 'FLOAT', '0.0'),
        ('total_credits_earned', 'INTEGER', '0'),
        ('total_credits_attempted', 'INTEGER', '0'),
        ('auto_promotion_enabled', 'BOOLEAN', '1'),
    ]
    
    added = 0
    for col_name, col_type, default_value in columns_to_add:
        if col_name not in existing_columns:
            try:
                sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type} DEFAULT {default_value}"
                db.session.execute(text(sql))
                db.session.commit()
                print(f"✅ Added column: {col_name}")
                added += 1
            except Exception as e:
                print(f"⚠️ Could not add {col_name}: {e}")
        else:
            print(f"⏭️ Column already exists: {col_name}")
    
    if added == 0:
        print("\n✅ All columns already exist!")
    else:
        print(f"\n✅ Added {added} new columns!")
    
    # Verify final columns
    inspector = inspect(db.engine)
    final_columns = [c['name'] for c in inspector.get_columns('users')]
    print(f"\nFinal columns: {sorted(final_columns)}")