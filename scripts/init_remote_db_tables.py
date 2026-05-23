# FILE: init_db_tables.py
# LOCATION: /init_db_tables.py
# PURPOSE: Initialize database tables WITHOUT importing the full app

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("\n" + "=" * 60)
print("🚀 SUBMITA DATABASE INITIALIZATION")
print("=" * 60)

# Get database URL
db_url = os.environ.get('DATABASE_URL', '')

if not db_url:
    print("📁 Using SQLite database")
    db_url = 'sqlite:///submita.db'
else:
    # Convert postgres:// to postgresql://
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    print(f"📁 Using PostgreSQL database")

# Hide password for display
display_url = db_url
if '@' in display_url:
    parts = display_url.split('@')
    if ':' in parts[0]:
        user_pass = parts[0].split('://')[-1] if '://' in parts[0] else parts[0]
        if ':' in user_pass:
            hidden = user_pass.split(':')[0] + ':****'
            display_url = display_url.replace(user_pass, hidden)
print(f"📍 Database: {display_url[:60]}...")

# Create standalone SQLAlchemy engine (no Flask)
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from werkzeug.security import generate_password_hash

# Create engine WITHOUT any special options
if 'sqlite' in db_url:
    engine = create_engine(db_url, connect_args={'check_same_thread': False})
else:
    # PostgreSQL - NO check_same_thread
    engine = create_engine(db_url)

Base = declarative_base()

# Define User model (matching your models.py structure)
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(120), unique=True, nullable=False)
    matric = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    password = Column(String(200), nullable=False)
    code = Column(String(10))
    verified = Column(Boolean, default=False)
    role = Column(String(20), default='student')
    department = Column(String(100))
    college = Column(String(100))
    level = Column(String(10))
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime)
    account_active = Column(Boolean, default=True)
    student_id = Column(String(50), unique=True)
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime)
    verification_token = Column(String(100), unique=True)
    token_expires_at = Column(DateTime)
    registration_number = Column(Integer)
    department_id = Column(Integer)
    college_id = Column(Integer)

# Create all tables
print("\n📦 Creating database tables...")
Base.metadata.create_all(engine)
print("✅ Tables created successfully!")

# Create session
Session = sessionmaker(bind=engine)
session = Session()

def create_user_if_not_exists(matric, email, name, password, role, **kwargs):
    """Helper to create user if doesn't exist"""
    existing = session.query(User).filter_by(matric=matric).first()
    if existing:
        print(f"ℹ️ User {matric} already exists")
        return None
    
    user = User(
        email=email,
        matric=matric,
        name=name,
        password=generate_password_hash(password),
        code='123456',
        verified=True,
        role=role,
        account_active=True,
        email_verified=True,
        **kwargs
    )
    session.add(user)
    print(f"✅ Created: {name} ({role})")
    return user

print("\n👤 Creating default users...")

# Create Admin
create_user_if_not_exists(
    matric='ADMIN001',
    email='admin@submita.com',
    name='System Administrator',
    password='Admin123!',
    role='admin'
)

# Create Lecturer
create_user_if_not_exists(
    matric='LEC001',
    email='lecturer@mouau.edu.ng',
    name='Dr. John Okonkwo',
    password='Lecturer123!',
    role='lecturer',
    department='Computer Science',
    college='College of Natural Sciences'
)

# Create Student
create_user_if_not_exists(
    matric='STU001',
    email='student@gmail.com',
    name='Test Student',
    password='Student123!',
    role='student',
    level='300',
    department='Computer Science',
    college='College of Natural Sciences'
)

# Commit all changes
try:
    session.commit()
    print("\n✅ All users saved successfully!")
except Exception as e:
    print(f"\n❌ Error saving users: {e}")
    session.rollback()

# Verify users were created
print("\n📊 Users in database:")
users = session.query(User).all()
for user in users:
    print(f"   • {user.name} ({user.role}) - {user.email}")

session.close()

print("\n" + "=" * 60)
print("✅ DATABASE INITIALIZATION COMPLETE!")
print("=" * 60)
print("\n🔑 Login Credentials:")
print("   Admin:    ADMIN001 / Admin123!")
print("   Lecturer: LEC001 / Lecturer123!")
print("   Student:  STU001 / Student123!")
print("=" * 60)
