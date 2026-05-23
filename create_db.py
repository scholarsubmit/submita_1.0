# FILE: create_db.py
from app import app, db

print("⏳ Establishing application context and connecting to database...")
with app.app_context():
    try:
        # This reads your models.py imports from app.py and maps them
        db.create_all()
        print("✅ Production PostgreSQL tables generated successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")