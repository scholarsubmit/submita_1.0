# FILE: init_remote_db.py
# LOCATION: /init_remote_db.py
# PURPOSE: Initialize remote PostgreSQL database

from app import app, db
from models import User, UserRole, College, Department
from werkzeug.security import generate_password_hash
import os
from dotenv import load_dotenv

load_dotenv()

def init_remote_database():
    """Initialize remote PostgreSQL database with tables and default data"""
    
    print("\n" + "=" * 60)
    print("INITIALIZING REMOTE POSTGRESQL DATABASE")
    print("=" * 60)
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in .env file")
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
    
    print(f"\n📡 Connecting to: {display_url}")
    
    try:
        with app.app_context():
            # Create all tables
            print("\n📦 Creating database tables...")
            db.create_all()
            print("✅ Tables created successfully!")
            
            # Create default admin
            admin = User.query.filter_by(matric='ADMIN001').first()
            if not admin:
                admin = User(
                    email='admin@submita.com',
                    matric='ADMIN001',
                    name='System Administrator',
                    password=generate_password_hash('Admin123!'),
                    code='123456',
                    verified=True,
                    role=UserRole.ADMIN,
                    account_active=True,
                    email_verified=True
                )
                db.session.add(admin)
                print("✅ Admin user created")
            else:
                print("ℹ️ Admin user already exists")
            
            # Create default lecturer
            lecturer = User.query.filter_by(matric='LEC001').first()
            if not lecturer:
                lecturer = User(
                    email='lecturer@mouau.edu.ng',
                    matric='LEC001',
                    name='Dr. John Okonkwo',
                    password=generate_password_hash('Lecturer123!'),
                    code='123456',
                    verified=True,
                    role=UserRole.LECTURER,
                    account_active=True,
                    email_verified=True,
                    department='Computer Science',
                    college='College of Natural Sciences'
                )
                db.session.add(lecturer)
                print("✅ Lecturer user created")
            else:
                print("ℹ️ Lecturer user already exists")
            
            # Create default student
            student = User.query.filter_by(matric='STU001').first()
            if not student:
                student = User(
                    email='student@gmail.com',
                    matric='STU001',
                    name='Test Student',
                    password=generate_password_hash('Student123!'),
                    code='123456',
                    verified=True,
                    role=UserRole.STUDENT,
                    level='300',
                    account_active=True,
                    email_verified=True,
                    department='Computer Science',
                    college='College of Natural Sciences'
                )
                db.session.add(student)
                print("✅ Student user created")
            else:
                print("ℹ️ Student user already exists")
            
            db.session.commit()
            
            print("\n" + "=" * 60)
            print("✅ REMOTE DATABASE INITIALIZATION COMPLETE!")
            print("=" * 60)
            print("\n🔑 Default Login Credentials:")
            print("   Admin:    ADMIN001 / Admin123!")
            print("   Lecturer: LEC001 / Lecturer123!")
            print("   Student:  STU001 / Student123!")
            print("=" * 60)
            
            return True
            
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        db.session.rollback()
        return False

if __name__ == '__main__':
    init_remote_database()