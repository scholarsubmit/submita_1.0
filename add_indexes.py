# FILE: add_indexes.py
# LOCATION: /add_indexes.py
# FIXES: Add database indexes for faster queries

import sqlite3
import os

def add_indexes():
    """Add missing indexes to improve query performance"""
    
    db_path = 'submita.db'
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found. Run the app first to create it.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get existing indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    existing_indexes = [row[0] for row in cursor.fetchall()]
    
    indexes_to_create = [
        # Users table indexes
        ('idx_users_email', 'users', 'email'),
        ('idx_users_matric', 'users', 'matric'),
        ('idx_users_role', 'users', 'role'),
        ('idx_users_created_at', 'users', 'created_at'),
        ('idx_users_student_id', 'users', 'student_id'),
        
        # Assignments table indexes
        ('idx_assignments_created_by', 'assignments', 'created_by'),
        ('idx_assignments_deadline', 'assignments', 'deadline'),
        ('idx_assignments_is_published', 'assignments', 'is_published'),
        ('idx_assignments_created_at', 'assignments', 'created_at'),
        
        # Submissions table indexes
        ('idx_submissions_assignment_id', 'submissions', 'assignment_id'),
        ('idx_submissions_student_id', 'submissions', 'student_id'),
        ('idx_submissions_submitted_at', 'submissions', 'submitted_at'),
        ('idx_submissions_grade', 'submissions', 'grade'),
        ('idx_submissions_is_draft', 'submissions', 'is_draft'),
        
        # Activity logs indexes
        ('idx_activity_logs_user_id', 'activity_logs', 'user_id'),
        ('idx_activity_logs_timestamp', 'activity_logs', 'timestamp'),
        
        # Lecturer verification indexes
        ('idx_lecturer_verification_code', 'lecturer_verifications', 'verification_code'),
        ('idx_lecturer_verification_email', 'lecturer_verifications', 'email'),
        ('idx_lecturer_verification_expires', 'lecturer_verifications', 'expires_at'),
    ]
    
    created_count = 0
    
    for idx_name, table, column in indexes_to_create:
        if idx_name not in existing_indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
                print(f"✅ Created index: {idx_name} on {table}({column})")
                created_count += 1
            except Exception as e:
                print(f"❌ Failed to create {idx_name}: {e}")
        else:
            print(f"⏭️  Index already exists: {idx_name}")
    
    # Create composite indexes for common queries
    composite_indexes = [
        ('idx_submissions_assignment_student', 'submissions', 'assignment_id, student_id'),
        ('idx_assignments_lecturer_published', 'assignments', 'created_by, is_published'),
        ('idx_users_role_verified', 'users', 'role, verified'),
    ]
    
    for idx_name, table, columns in composite_indexes:
        if idx_name not in existing_indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})")
                print(f"✅ Created composite index: {idx_name} on {table}({columns})")
                created_count += 1
            except Exception as e:
                print(f"❌ Failed to create {idx_name}: {e}")
        else:
            print(f"⏭️  Composite index already exists: {idx_name}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 50)
    print(f"✅ Index creation complete! {created_count} new indexes added.")
    print("=" * 50)
    
    # Run ANALYZE to update query planner
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("ANALYZE")
    conn.close()
    print("📊 Database statistics updated (ANALYZE completed).")

if __name__ == "__main__":
    print("=" * 50)
    print("SUBMITA DATABASE INDEX OPTIMIZER")
    print("=" * 50)
    add_indexes()