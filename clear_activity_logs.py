# FILE: clear_activity_logs.py
from app import app, db
from models import ActivityLog

with app.app_context():
    # Rollback any pending transaction
    db.session.rollback()
    
    # Clear activity logs
    ActivityLog.query.delete()
    db.session.commit()
    
    # Reset the sequence
    from sqlalchemy import text
    db.session.execute(text("SELECT setval('activity_logs_id_seq', 1)"))
    db.session.commit()
    
    print("✅ Activity logs cleared and sequence reset")