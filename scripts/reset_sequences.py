# FILE: reset_sequences.py
# Run this to reset all ID sequences in PostgreSQL

from app import app, db
from sqlalchemy import text

with app.app_context():
    # Reset sequence for activity_logs
    try:
        db.session.execute(text("SELECT setval('activity_logs_id_seq', COALESCE((SELECT MAX(id) FROM activity_logs), 1))"))
        db.session.commit()
        print("✅ Reset activity_logs_id_seq")
    except Exception as e:
        print(f"Error resetting activity_logs sequence: {e}")
    
    # Reset sequences for all tables that have id columns
    tables = ['users', 'assignments', 'submissions', 'lecturer_verifications', 'colleges', 'departments', 'courses', 'semesters', 'student_enrollments', 'verification_codes', 'lecturer_registration_requests']
    
    for table in tables:
        try:
            db.session.execute(text(f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 1))"))
            db.session.commit()
            print(f"✅ Reset {table}_id_seq")
        except Exception as e:
            print(f"Could not reset {table}_id_seq: {e}")