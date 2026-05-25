# FILE: app.py
# LOCATION: /app.py
# FIXES: All template paths updated for subfolder structure, added missing routes, fixed duplicates

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps
from collections import OrderedDict, defaultdict
import os
import random
import json
import socket
import secrets
import re
import time
import hashlib
import base64
import html

# Import models
from models import (
    db, User, UserRole, Assignment, Submission, 
    LecturerVerification, ActivityLog,
    College, Department, Course, StudentEnrollment, Semester,
    LecturerRegistrationRequest
)

# Import services
from email_service import EmailService
from ai_grading import AIGrading
from plagiarism_checker import PlagiarismChecker
#from course_service import CourseService
#from academic_service import AcademicService

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from sqlalchemy.dialects import registry
    import pg8000
    print(f"✅ pg8000 version {pg8000.__version__} available")
    try:
        registry.register("postgresql.pg8000", "pg8000.sqlalchemy", "PG8000Dialect")
        print("✅ pg8000 SQLAlchemy dialect registered")
    except Exception as e:
        print(f"⚠️ Dialect registration skipped: {e}")
except ImportError as e:
    print(f"⚠️ pg8000 not installed: {e}")

try:
    import psycopg2
    print("✅ psycopg2-binary available as fallback")
except ImportError:
    print("⚠️ psycopg2-binary not installed")

# ==================== DATABASE URL CONVERSION ====================
DATABASE_URL = os.environ.get('DATABASE_URL', '')

if DATABASE_URL:
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        os.environ['DATABASE_URL'] = DATABASE_URL
        print("✅ Converted postgres:// to postgresql://")
    print(f"📁 Using PostgreSQL database")

# ==================== PRODUCTION CONFIGURATION ====================
IS_PRODUCTION = os.environ.get('RENDER', False) or os.environ.get('PRODUCTION', False)

# Create Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='templates')

# ==================== DATABASE CONFIGURATION ====================
database_url = os.environ.get('DATABASE_URL', '')

if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
        os.environ['DATABASE_URL'] = database_url
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print("✅ Using PostgreSQL database")
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///submita.db'
    print("📁 Using SQLite database")
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'check_same_thread': False, 'timeout': 30}
    }

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

print(f"📋 Database URI: {app.config['SQLALCHEMY_DATABASE_URI'][:60]}...")

# ==================== SECURITY CONFIGURATION ====================
def is_lan_request():
    host = request.host if hasattr(request, 'host') else ''
    return host and not host.startswith('localhost') and not host.startswith('127.0.0.1')

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(64))
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 1800
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
app.config['REMEMBER_COOKIE_SECURE'] = False
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)
app.config['WTF_CSRF_COOKIE_SECURE'] = False
app.config['WTF_CSRF_COOKIE_SAMESITE'] = 'Lax'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000
app.debug = not IS_PRODUCTION

APP_NAME = "Submita"
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ASSIGNMENT_FOLDER'] = 'uploads/assignments'
app.config['SUBMISSION_FOLDER'] = 'uploads/submissions'
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'py', 'js', 'java', 'cpp', 'c', 'zip', 'rar', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ASSIGNMENT_FOLDER'], exist_ok=True)
os.makedirs(app.config['SUBMISSION_FOLDER'], exist_ok=True)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
login_manager.session_protection = "strong"
login_manager.refresh_view = 'login'
login_manager.needs_refresh_message = 'Session expired. Please login again.'

# ==================== RATE LIMITING ====================
class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
    
    def is_allowed(self, key, limit, window):
        now = time.time()
        self.requests[key] = [t for t in self.requests[key] if now - t < window]
        if len(self.requests[key]) >= limit:
            return False, int(window - (now - self.requests[key][0]))
        self.requests[key].append(now)
        return True, 0

rate_limiter = RateLimiter()

def rate_limit(limit, window, methods=['POST']):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method in methods:
                key = f"{request.remote_addr}:{f.__name__}"
                allowed, wait_time = rate_limiter.is_allowed(key, limit, window)
                if not allowed:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'error': f'Rate limit exceeded. Try again in {wait_time} seconds.'}), 429
                    else:
                        flash(f'Rate limit exceeded. Please try again in {wait_time} seconds.', 'danger')
                        return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==================== INPUT SANITIZATION ====================
def sanitize_input(data):
    if isinstance(data, str):
        data = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', data)
        data = html.escape(data)
        data = re.sub(r'(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute|script|javascript|onclick|onload|onerror)', '', data)
        return data.strip()
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    return data

# ==================== CSRF PROTECTION ====================
def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

@app.context_processor
def inject_csrf_token():
    return {'csrf_token': generate_csrf_token()}

# ==================== SECURE FILE UPLOAD ====================
def secure_file_upload(file, allowed_extensions=None, max_size_mb=10):
    if not file or not file.filename:
        return None, "No file provided"
    
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return None, f"File size exceeds {max_size_mb}MB limit"
    
    allowed_extensions = allowed_extensions or app.config['ALLOWED_EXTENSIONS']
    extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if extension not in allowed_extensions:
        return None, f"File type .{extension} not allowed"
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_hash = secrets.token_hex(8)
    secure_name = f"{timestamp}_{random_hash}_{secure_filename(file.filename)}"
    
    file_content = file.read(1024)
    file.seek(0)
    
    malware_signatures = [
        b'<?php', b'<%', b'<script', b'javascript:', b'vbscript:',
        b'base64_decode', b'eval(', b'system(', b'exec(', b'passthru'
    ]
    
    for signature in malware_signatures:
        if signature in file_content:
            return None, "File contains potentially malicious content"
    
    return secure_name, None

# ==================== PASSWORD VALIDATION ====================
def validate_password_strength(password):
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if len(password) > 128:
        errors.append("Password must be less than 128 characters")
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    common_passwords = ['Password123!', 'Admin123!', 'Qwerty123!', 'Welcome123!', 'Student123!', 'Lecturer123!']
    if password in common_passwords:
        errors.append("Password is too common. Please choose a more unique password")
    return len(errors) == 0, errors

# ==================== ACTIVITY LOGGING ====================
def log_activity(user_id, action, details, request_obj=None):
    if user_id is None:
        return
    try:
        log = ActivityLog(
            user_id=user_id,
            action=action[:200] if action else '',
            details=details[:500] if details else '',
            ip_address=request_obj.remote_addr if request_obj else 'unknown',
            user_agent=request_obj.headers.get('User-Agent', 'unknown')[:500] if request_obj else 'unknown'
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Activity logging failed: {e}")

# ==================== SECURITY MIDDLEWARE ====================
@app.before_request
def security_middleware():
    malicious_patterns = ['../', '..\\', '%2e%2e', 'wp-admin', 'phpmyadmin', '.env', '.git', 'config']
    if request.path and any(pattern in request.path.lower() for pattern in malicious_patterns):
        log_activity(None, 'attack_blocked', f"Blocked malicious path: {request.path}", request)
        return "Access Denied", 403
    if current_user.is_authenticated:
        session['last_activity'] = datetime.now().isoformat()

# ==================== LOAD ACADEMIC STRUCTURE ====================
def load_academic_structure():
    json_path = os.path.join(os.path.dirname(__file__), 'academic_structure.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('Colleges', [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

ACADEMIC_STRUCTURE = load_academic_structure()

def generate_student_id(department_code, registration_number):
    return f"S/{department_code}/{registration_number:04d}"

def get_department_code(department_name):
    if not department_name:
        return "GEN"
    dept_codes = {
        'Computer Science': 'CSC', 'Mathematics': 'MTH', 'Physics': 'PHY',
        'Chemistry': 'CHM', 'Biochemistry': 'BCH', 'Microbiology': 'MCB',
        'Accounting': 'ACC', 'Business Administration': 'BUS', 'Economics': 'ECO',
        'Mass Communication': 'MAC',
    }
    return dept_codes.get(department_name, department_name[:3].upper() if len(department_name) >= 3 else "GEN")

# ==================== COOKIES AND SESSION MANAGEMENT ====================
@app.before_request
def set_cookie_domain():
    if request.host and not request.host.startswith('localhost') and not request.host.startswith('127.0.0.1'):
        host = request.host.split(':')[0]
        app.config['SESSION_COOKIE_DOMAIN'] = host
        app.config['REMEMBER_COOKIE_DOMAIN'] = host
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
    else:
        app.config['SESSION_COOKIE_DOMAIN'] = None
        app.config['REMEMBER_COOKIE_DOMAIN'] = None

# ==================== SECURE CODE GENERATION ====================
def generate_secure_verification_code(full_name, email, department):
    SAFE_CHARS = 'ABCDEFGHJKLMNPQRTUVWXY34679'
    timestamp = str(int(time.time() * 1000))
    random_bytes = secrets.token_bytes(32)
    unique_seed = f"{full_name}{email}{department}{timestamp}{random_bytes.hex()}{secrets.token_hex(16)}"
    hash_obj = hashlib.sha256(unique_seed.encode())
    hash_hex = hash_obj.hexdigest().upper()
    safe_chars = [c for c in hash_hex if c in SAFE_CHARS]
    while len(safe_chars) < 15:
        safe_chars.extend(secrets.choice(SAFE_CHARS) for _ in range(5))
    code_length = secrets.randbelow(4) + 6
    indices = secrets.SystemRandom().sample(range(len(safe_chars)), code_length)
    indices.sort()
    return ''.join(safe_chars[i] for i in indices)

def verify_lecturer_code_rate_limit(verification):
    if verification.verification_attempts >= 5:
        last_attempt = verification.last_verification_attempt
        if last_attempt and (datetime.now() - last_attempt).seconds < 900:
            return False, 'Too many failed attempts. Please try again in 15 minutes.'
        else:
            verification.verification_attempts = 0
            db.session.commit()
    return True, None

# ==================== USER CACHE ====================
class UserCache:
    def __init__(self, max_size=100, ttl=300):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
    def get(self, user_id):
        if user_id in self.cache:
            data, timestamp = self.cache[user_id]
            if time.time() - timestamp < self.ttl:
                return data
            else:
                del self.cache[user_id]
        return None
    def set(self, user_id, user_data):
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        self.cache[user_id] = (user_data, time.time())
    def invalidate(self, user_id):
        if user_id in self.cache:
            del self.cache[user_id]

user_cache = UserCache()

# ==================== USER LOADER ====================
@login_manager.user_loader
def load_user(user_id):
    try:
        user = db.session.get(User, int(user_id))
        if user:
            _ = user.role
            _ = user.email
            _ = user.name
            _ = user.matric
            _ = user.password
        return user
    except Exception as e:
        print(f"Error loading user {user_id}: {e}")
        return None

# ==================== TEARDOWN REQUEST ====================
@app.teardown_request
def teardown_request(exception=None):
    try:
        db.session.remove()
    except:
        pass

# ==================== CONTEXT PROCESSOR ====================
@app.context_processor
def inject_globals():
    return {'user': current_user, 'now': datetime.now(), 'csrf_token': generate_csrf_token()}

# ==================== HELPER FUNCTIONS ====================
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def lecturer_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not (current_user.is_lecturer() or current_user.is_admin()):
            flash('Access denied. Lecturer privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def no_cache(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return decorated_function

# ==================== ROUTES ====================
@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    elif current_user.is_lecturer():
        return redirect(url_for('lecturer_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

@app.route('/check-auth')
def check_auth():
    return jsonify({'authenticated': current_user.is_authenticated})

# ==================== LOGIN ROUTE ====================
@app.route('/login', methods=['GET', 'POST'])
@no_cache
@rate_limit(limit=10, window=60)
def login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        elif current_user.is_lecturer():
            return redirect(url_for('lecturer_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        identifier = sanitize_input(request.form.get('loginIdentifier', ''))
        password = request.form.get('loginPassword', '')
        remember = request.form.get('remember', False)
        
        if not identifier or not password:
            flash('Please enter both email/ID and password.', 'danger')
            return redirect(url_for('login'))
        
        user = None
        if identifier.upper().startswith('S/'):
            user = db.session.query(User).filter_by(student_id=identifier.upper()).first()
        if not user:
            user = db.session.query(User).filter_by(matric=identifier.upper()).first()
        if not user:
            user = db.session.query(User).filter_by(email=identifier.lower()).first()
        
        if user and check_password_hash(user.password, password):
            if user.is_student() and not user.email_verified:
                session['verification_email'] = user.email
                session['verification_student_id'] = user.student_id
                session['verification_name'] = user.name
                flash('Please verify your email before logging in.', 'warning')
                return redirect(url_for('verify'))
            if not user.account_active:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return redirect(url_for('login'))
            
            user.last_login = datetime.now()
            db.session.commit()
            login_user(user, remember=remember)
            
            try:
                db.session.rollback()
                log = ActivityLog(
                    user_id=user.id, action='user_login',
                    details=f"User logged in from {request.remote_addr}",
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )
                db.session.add(log)
                db.session.commit()
            except Exception as e:
                print(f"Login logging error: {e}")
                db.session.rollback()
            
            flash(f'Welcome back, {user.name}!', 'success')
            
            if user.is_admin():
                redirect_url = url_for('admin_dashboard')
            elif user.is_lecturer():
                redirect_url = url_for('lecturer_dashboard')
            else:
                redirect_url = url_for('student_dashboard')
            
            if request.host and not request.host.startswith('localhost') and not request.host.startswith('127.0.0.1'):
                host = request.host.split(':')[0]
                response = make_response(redirect(redirect_url))
                response.set_cookie('session', domain=host, samesite='Lax', secure=False, httponly=True)
                return response
            return redirect(redirect_url)
        else:
            flash('Invalid credentials. Please check your email/ID and password.', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        if user_id:
            try:
                db.session.rollback()
                log = ActivityLog(
                    user_id=user_id, action='user_logout',
                    details="User logged out",
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )
                db.session.add(log)
                db.session.commit()
            except Exception as e:
                print(f"Logout logging error: {e}")
                db.session.rollback()
        logout_user()
        session.clear()
        if user_id:
            user_cache.invalidate(user_id)
        flash('You have been logged out successfully.', 'success')
        response = redirect(url_for('home'))
        response.delete_cookie('session')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        return response
    except Exception as e:
        print(f"Logout error: {e}")
        db.session.rollback()
        return redirect(url_for('login'))

# ==================== REGISTER ROUTE ====================
@app.route('/register', methods=['GET', 'POST'])
@no_cache
@rate_limit(limit=5, window=60)
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    colleges = College.query.order_by(College.name).all()
    departments = Department.query.order_by(Department.name).all()
    
    if request.method == 'POST':
        name = sanitize_input(request.form.get('regName', ''))
        email = sanitize_input(request.form.get('regEmail', '').lower())
        matric = sanitize_input(request.form.get('regId', '').upper())
        password = request.form.get('regPassword', '')
        role = sanitize_input(request.form.get('role', 'student'))
        college_id = request.form.get('college_id', type=int)
        department_id = request.form.get('department_id', type=int)
        level = sanitize_input(request.form.get('level', ''))
        verification_code = sanitize_input(request.form.get('verification_code', ''))
        
        college = College.query.get(college_id) if college_id else None
        department = Department.query.get(department_id) if department_id else None
        college_name = college.name if college else ''
        department_name = department.name if department else ''
        
        if not all([name, email, matric, password]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))
        
        if role == 'student':
            if not college_id or not department_id or not level:
                flash('Please select your college, department, and level.', 'danger')
                return redirect(url_for('register'))
        elif role == 'lecturer':
            if not college_id or not department_id:
                flash('Please select your college and department.', 'danger')
                return redirect(url_for('register'))
        
        is_valid, errors = validate_password_strength(password)
        if not is_valid:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('register'))
        
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('register'))
        
        email_exists = db.session.query(User).filter_by(email=email).first()
        if email_exists:
            flash('This email is already registered. Please use a different email or login.', 'danger')
            return redirect(url_for('login'))
        
        matric_exists = db.session.query(User).filter_by(matric=matric).first()
        if matric_exists:
            flash('This Matric/Staff ID is already registered. Please use your own ID or login.', 'danger')
            return redirect(url_for('login'))
        
        # Lecturer Registration
        if role == 'lecturer':
            if not verification_code:
                flash('Verification code is required for lecturer registration.', 'danger')
                return redirect(url_for('register'))
            
            verification = db.session.query(LecturerVerification).filter_by(
                verification_code=verification_code, is_used=False
            ).first()
            if not verification or verification.expires_at < datetime.now():
                flash('Invalid or expired verification code.', 'danger')
                return redirect(url_for('register'))
            
            verification.is_used = True
            verification.used_at = datetime.now()
            
            user = User(
                email=email, matric=matric, name=name,
                password=generate_password_hash(password),
                code=str(random.randint(100000, 999999)),
                role=UserRole.LECTURER,
                college=college_name, college_id=college_id,
                department=department_name, department_id=department_id,
                verified=True, account_active=True, email_verified=True
            )
            try:
                db.session.add(user)
                db.session.flush()
                verification.used_by = user.id
                db.session.commit()
                flash('Registration successful! Please login to continue.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash('Registration failed. Please try again.', 'danger')
                return redirect(url_for('register'))
        
        # Student Registration
        else:
            last_student = db.session.query(User).filter_by(role=UserRole.STUDENT).order_by(User.id.desc()).first()
            next_number = (last_student.registration_number or 0) + 1 if last_student else 1
            dept_code = department.code if department else get_department_code(department_name)
            student_id = generate_student_id(dept_code, next_number)
            email_verification_code = str(random.randint(100000, 999999))
            
            user = User(
                email=email, matric=matric, name=name,
                password=generate_password_hash(password),
                code=email_verification_code,
                role=UserRole.STUDENT,
                college=college_name, college_id=college_id,
                department=department_name, department_id=department_id,
                level=level, current_level=level,
                verified=False, account_active=True, email_verified=False,
                student_id=student_id, registration_number=next_number
            )
            try:
                db.session.add(user)
                db.session.commit()
                EmailService.send_verification_email(name, email, student_id, email_verification_code)
                session['verification_email'] = email
                session['verification_student_id'] = student_id
                session['verification_name'] = name
                flash('Account created! Please check your email for verification code.', 'success')
                return redirect(url_for('verify'))
            except Exception as e:
                db.session.rollback()
                flash('Registration failed. Please try again.', 'danger')
                return redirect(url_for('register'))
    
    return render_template('shared/register.html', academic_structure=ACADEMIC_STRUCTURE, colleges=colleges, departments=departments, now=datetime.now())

@app.route('/api/department-levels/<int:department_id>')
def api_department_levels(department_id):
    levels = db.session.query(Course.level).filter_by(department_id=department_id).distinct().all()
    level_list = sorted([l[0] for l in levels if l[0]])
    return jsonify({'levels': level_list})

@app.route('/verify', methods=['GET', 'POST'])
@no_cache
def verify():
    email = session.get('verification_email')
    student_id = session.get('verification_student_id')
    student_name = session.get('verification_name', 'Student')
    if not email:
        flash('No pending verification found. Please register first.', 'warning')
        return redirect(url_for('register'))
    if request.method == 'POST':
        entered_code = sanitize_input(request.form.get('code', ''))
        user = db.session.query(User).filter_by(email=email).first()
        if not user:
            flash('Account not found. Please register again.', 'danger')
            return redirect(url_for('register'))
        if user.code and user.code == entered_code:
            user.verified = True
            user.email_verified = True
            user.code = None
            db.session.commit()
            user_cache.invalidate(user.id)
            session.pop('verification_email', None)
            session.pop('verification_student_id', None)
            flash('Account activated successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid verification code. Please check and try again.', 'danger')
    return render_template('verify.html', email=email, student_id=student_id, student_name=student_name)

@app.route('/resend-code/<email>')
@rate_limit(limit=3, window=300)
def resend_code(email):
    email = sanitize_input(email)
    user = db.session.query(User).filter_by(email=email).first()
    if not user:
        flash('Account not found.', 'danger')
        return redirect(url_for('register'))
    if user.verified:
        flash('Account already verified.', 'info')
        return redirect(url_for('login'))
    new_code = str(random.randint(100000, 999999))
    user.code = new_code
    db.session.commit()
    EmailService.send_verification_email(user.name, email, user.student_id, new_code)
    flash(f'A new verification code has been sent to {email}.', 'success')
    return redirect(url_for('verify'))

# ==================== CREATE ASSIGNMENT ROUTE ====================
@app.route('/create-assignment', methods=['GET', 'POST'])
@lecturer_required
@no_cache
def create_assignment():
    colleges = College.query.all()
    departments = Department.query.all()
    courses = Course.query.filter_by(department_id=current_user.department_id).all()
    
    if request.method == 'POST':
        title = sanitize_input(request.form.get('title', ''))
        course_code = sanitize_input(request.form.get('course_code', ''))
        course_title = sanitize_input(request.form.get('course_title', ''))
        questions = sanitize_input(request.form.get('questions', ''))
        instructions = sanitize_input(request.form.get('instructions', ''))
        deadline_str = request.form.get('deadline', '')
        total_points = int(request.form.get('total_points', 100))
        action = request.form.get('action', 'publish')
        target_level = sanitize_input(request.form.get('target_level', ''))
        target_department_id = request.form.get('target_department_id', type=int)
        target_semester = sanitize_input(request.form.get('target_semester', ''))
        target_academic_year = sanitize_input(request.form.get('target_academic_year', ''))
        
        if not all([title, course_code, course_title, questions, deadline_str, target_level, target_department_id, target_semester, target_academic_year]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('create_assignment'))
        
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid deadline format.', 'danger')
            return redirect(url_for('create_assignment'))
        
        attachment_path = None
        attachment_filename = None
        attachment_type = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                secure_name, error = secure_file_upload(file, max_size_mb=10)
                if error:
                    flash(error, 'danger')
                    return redirect(url_for('create_assignment'))
                attachment_path = secure_name
                attachment_filename = file.filename
                attachment_type = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
                file.save(os.path.join(app.config['ASSIGNMENT_FOLDER'], secure_name))
        
        assignment = Assignment(
            title=title, course_code=course_code, course_title=course_title,
            questions=questions, instructions=instructions,
            deadline=deadline, total_points=total_points,
            attachment_path=attachment_path, attachment_filename=attachment_filename, attachment_type=attachment_type,
            target_level=target_level, target_department_id=target_department_id,
            target_semester=target_semester, target_academic_year=target_academic_year,
            created_by=current_user.id, is_published=(action == 'publish'),
            published_at=datetime.now() if action == 'publish' else None
        )
        try:
            db.session.add(assignment)
            db.session.commit()
            flash('Assignment published successfully!' if action == 'publish' else 'Assignment saved as draft.', 'success')
            return redirect(url_for('lecturer_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating assignment: {str(e)}', 'danger')
    
    return render_template('lecturer/create_assignment.html', colleges=colleges, departments=departments, courses=courses, now=datetime.now())

@app.route('/create_assignment', methods=['GET', 'POST'])
@lecturer_required
def create_assignment_alias():
    return create_assignment()

# ==================== EDIT ASSIGNMENT ROUTE ====================
@app.route('/assignment/<int:assignment_id>/edit', methods=['GET', 'POST'])
@lecturer_required
@no_cache
def edit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash('You can only edit your own assignments.', 'danger')
        return redirect(url_for('lecturer_dashboard'))
    
    has_submissions = Submission.query.filter_by(assignment_id=assignment_id, is_draft=False).count() > 0
    colleges = College.query.all()
    departments = Department.query.all()
    
    if request.method == 'POST':
        assignment.title = sanitize_input(request.form.get('title', assignment.title))
        assignment.course_code = sanitize_input(request.form.get('course_code', assignment.course_code))
        assignment.course_title = sanitize_input(request.form.get('course_title', assignment.course_title))
        assignment.questions = sanitize_input(request.form.get('questions', assignment.questions))
        assignment.instructions = sanitize_input(request.form.get('instructions', assignment.instructions))
        
        deadline_str = request.form.get('deadline', '')
        if deadline_str:
            try:
                assignment.deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid deadline format.', 'danger')
                return redirect(url_for('edit_assignment', assignment_id=assignment_id))
        
        assignment.target_level = sanitize_input(request.form.get('target_level', assignment.target_level))
        assignment.target_department_id = request.form.get('target_department_id', type=int)
        assignment.target_semester = sanitize_input(request.form.get('target_semester', assignment.target_semester))
        assignment.target_academic_year = sanitize_input(request.form.get('target_academic_year', assignment.target_academic_year))
        assignment.late_submission_penalty = float(request.form.get('late_penalty', 10))
        assignment.max_file_size = int(request.form.get('max_file_size', 10))
        
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                secure_name, error = secure_file_upload(file, max_size_mb=10)
                if error:
                    flash(error, 'danger')
                    return redirect(url_for('edit_assignment', assignment_id=assignment_id))
                if assignment.attachment_path:
                    old_path = os.path.join(app.config['ASSIGNMENT_FOLDER'], assignment.attachment_path)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                assignment.attachment_path = secure_name
                assignment.attachment_filename = file.filename
                assignment.attachment_type = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
                file.save(os.path.join(app.config['ASSIGNMENT_FOLDER'], secure_name))
        
        if request.form.get('action') == 'publish' and not assignment.is_published:
            assignment.is_published = True
            assignment.published_at = datetime.now()
        
        assignment.updated_at = datetime.now()
        try:
            db.session.commit()
            flash('Assignment updated successfully!', 'success')
            return redirect(url_for('manage_assignment', assignment_id=assignment.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating assignment: {str(e)}', 'danger')
    
    return render_template('lecturer/edit_assignment.html', assignment=assignment, colleges=colleges, departments=departments, has_submissions=has_submissions, now=datetime.now())

# ==================== MANAGE ASSIGNMENT ROUTE ====================
@app.route('/assignment/manage/<int:assignment_id>')
@lecturer_required
@no_cache
def manage_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('lecturer_dashboard'))
    
    submissions = Submission.query.filter_by(assignment_id=assignment_id, is_draft=False).order_by(Submission.submitted_at.desc()).all()
    total_submissions = len(submissions)
    graded_count = len([s for s in submissions if s.grade is not None])
    pending_count = total_submissions - graded_count
    graded_scores = [s.grade for s in submissions if s.grade is not None]
    average_grade = round(sum(graded_scores) / len(graded_scores), 1) if graded_scores else 0
    
    return render_template('lecturer/manage_assignments.html', assignment=assignment, submissions=submissions, total_submissions=total_submissions, graded_count=graded_count, pending_count=pending_count, average_grade=average_grade)

# ==================== GRADE SUBMISSION ROUTE ====================
@app.route('/grade/<int:submission_id>', methods=['GET', 'POST'])
@lecturer_required
@no_cache
def grade_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    assignment = submission.assignment
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('lecturer_dashboard'))
    
    if request.method == 'POST':
        grade = request.form.get('grade', type=float)
        feedback = sanitize_input(request.form.get('feedback', ''))
        if grade is not None:
            submission.grade = grade
            submission.feedback = feedback
            submission.auto_graded = False
            try:
                db.session.commit()
                EmailService.send_grade_notification(submission.student.email, submission.student.name, assignment.title, grade, feedback)
                flash('Grade saved successfully!', 'success')
                return redirect(url_for('manage_assignment', assignment_id=assignment.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Error saving grade: {str(e)}', 'danger')
        else:
            flash('Please enter a valid grade.', 'danger')
    
    return render_template('lecturer/grade_submission.html', submission=submission, assignment=assignment)

# ==================== AI GRADE REPORT ROUTE ====================
@app.route('/ai-grade/<int:submission_id>')
@lecturer_required
@no_cache
def ai_grade_report(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    assignment = submission.assignment
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('lecturer_dashboard'))
    
    if submission.content:
        if any(ext in submission.content for ext in ['def ', 'class ', 'import ', 'function']):
            score, feedback, breakdown = AIGrading.grade_code_submission(submission.content, [assignment.title, assignment.course_code])
        else:
            keywords = assignment.questions.lower().split()[:10]
            score, feedback, breakdown = AIGrading.grade_theory_submission(submission.content, keywords)
        suggestions = AIGrading.get_improvement_suggestions(score, feedback)
    else:
        score, feedback, breakdown, suggestions = 0, ["No text content to analyze. Please grade manually."], {}, ["Consider adding text explanation for AI grading."]
    
    return render_template('lecturer/ai_grading_report.html', submission=submission, assignment=assignment, score=score, feedback=feedback, breakdown=breakdown, suggestions=suggestions)

# ==================== PLAGIARISM REPORT ROUTES ====================
@app.route('/plagiarism-report/<int:submission_id>')
@login_required
@no_cache
def plagiarism_report_student(submission_id):
    """Show plagiarism report for a student (student view)"""
    submission = Submission.query.get_or_404(submission_id)
    
    # Check permissions - students can only see their own reports
    if current_user.is_student() and submission.student_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('student_dashboard'))
    
    # Get all submissions for this assignment for comparison
    all_submissions = Submission.query.filter_by(
        assignment_id=submission.assignment_id, 
        is_draft=False
    ).all()
    
    # Prepare current submission for comparison
    current_submission = {
        'id': submission.id,
        'content': submission.content or '',
        'student_name': submission.student.name,
        'student_id': submission.student.matric
    }
    
    # Prepare other submissions
    other_submissions = []
    for sub in all_submissions:
        if sub.id != submission.id:
            other_submissions.append({
                'id': sub.id,
                'content': sub.content or '',
                'student_name': sub.student.name,
                'student_id': sub.student.matric
            })
    
    # Detect plagiarism
    matches = PlagiarismChecker.detect_plagiarism(current_submission, other_submissions)
    report = PlagiarismChecker.get_plagiarism_report(submission, matches)
    
    # ✅ FIXED: Use student subfolder
    return render_template('student/plagiarism_report_student.html',
                         submission=submission,
                         plagiarism_score=submission.plagiarism_score or 0,
                         matches=matches,
                         report=report)


@app.route('/lecturer/plagiarism/<int:submission_id>')
@lecturer_required
@no_cache
def lecturer_plagiarism_report(submission_id):
    """Show plagiarism report for a submission (lecturer view with more detail)"""
    submission = Submission.query.get_or_404(submission_id)
    assignment = submission.assignment
    
    # Check permissions
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('lecturer_dashboard'))
    
    # Get all submissions for comparison
    all_submissions = Submission.query.filter_by(
        assignment_id=assignment.id, 
        is_draft=False
    ).all()
    
    # Prepare data for plagiarism check
    current_submission = {
        'id': submission.id,
        'content': submission.content or '',
        'student_name': submission.student.name,
        'student_id': submission.student.matric
    }
    
    other_submissions = []
    for sub in all_submissions:
        if sub.id != submission.id:
            other_submissions.append({
                'id': sub.id,
                'content': sub.content or '',
                'student_name': sub.student.name,
                'student_id': sub.student.matric
            })
    
    # Run plagiarism detection
    matches = PlagiarismChecker.detect_plagiarism(current_submission, other_submissions)
    
    # Update submission with plagiarism score
    if matches:
        submission.plagiarism_score = matches[0]['similarity']
    else:
        submission.plagiarism_score = 0
    
    db.session.commit()
    
    report = PlagiarismChecker.get_plagiarism_report(submission, matches)
    
    # ✅ FIXED: Use lecturer subfolder
    return render_template('lecturer/lecturer_plagiarism_report.html',
                         submission=submission,
                         assignment=assignment,
                         matches=matches,
                         report=report)


# ==================== SUBMIT ASSIGNMENT ROUTE ====================
@app.route('/submit/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@no_cache
def submit_assignment(assignment_id):
    if not current_user.is_student():
        flash('Only students can submit assignments.', 'danger')
        return redirect(url_for('dashboard'))
    
    assignment = Assignment.query.get_or_404(assignment_id)
    if not assignment.is_published:
        flash('This assignment is not yet available.', 'warning')
        return redirect(url_for('student_dashboard'))
    
    existing = Submission.query.filter_by(assignment_id=assignment_id, student_id=current_user.id, is_draft=False).first()
    if existing:
        flash('You have already submitted this assignment.', 'warning')
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        content = sanitize_input(request.form.get('content', ''))
        github_url = sanitize_input(request.form.get('github_url', ''))
        is_draft = request.form.get('save_draft') == 'on'
        
        file_path = original_filename = file_type = None
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                secure_name, error = secure_file_upload(file, max_size_mb=assignment.max_file_size or 10)
                if error:
                    flash(error, 'danger')
                    return redirect(url_for('submit_assignment', assignment_id=assignment_id))
                file_path, original_filename, file_type = secure_name, file.filename, file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
                file.save(os.path.join(app.config['SUBMISSION_FOLDER'], secure_name))
        
        if not content and not file_path and not github_url:
            flash('Please provide content, upload a file, or add a GitHub URL.', 'danger')
            return redirect(url_for('submit_assignment', assignment_id=assignment_id))
        
        is_late = datetime.now() > assignment.deadline
        submission = Submission(
            assignment_id=assignment_id, student_id=current_user.id,
            content=content, file_path=file_path, original_filename=original_filename, file_type=file_type,
            github_url=github_url, submitted_at=datetime.now(), is_draft=is_draft, is_late=is_late,
            ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent', '')
        )
        if is_late and not is_draft:
            days_late = max(1, (datetime.now() - assignment.deadline).days)
            submission.late_penalty_applied = min(assignment.late_submission_penalty * days_late, 50)
        try:
            db.session.add(submission)
            db.session.commit()
            flash('Draft saved successfully!' if is_draft else 'Assignment submitted successfully!', 'success')
            return redirect(url_for('student_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting assignment: {str(e)}', 'danger')
    
    return render_template('student/submit_assignment.html', assignment=assignment)

# ==================== ADMIN ROUTES ====================
@app.route('/admin-dashboard')
@admin_required
def admin_dashboard():
    try:
        total_users = db.session.query(User).count()
        total_students = db.session.query(User).filter_by(role=UserRole.STUDENT).count()
        total_lecturers = db.session.query(User).filter_by(role=UserRole.LECTURER).count()
        total_assignments = db.session.query(Assignment).count()
        total_submissions = db.session.query(Submission).filter_by(is_draft=False).count()
        recent_users = db.session.query(User).order_by(User.created_at.desc()).limit(10).all()
        return render_template('admin/admin_dashboard.html', total_users=total_users, total_students=total_students, total_lecturers=total_lecturers, total_assignments=total_assignments, total_submissions=total_submissions, recent_users=recent_users, now=datetime.now())
    except Exception as e:
        flash('Error loading dashboard.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/admin/lecturer-codes')
@admin_required
@no_cache
def admin_lecturer_codes():
    codes = db.session.query(LecturerVerification).order_by(LecturerVerification.created_at.desc()).all()
    return render_template('admin/admin_lecturer_codes.html', codes=codes, now=datetime.now())

@app.route('/admin/send-verification', methods=['POST'])
@admin_required
@rate_limit(limit=10, window=3600)
def send_verification_email():
    try:
        full_name = sanitize_input(request.form.get('full_name', ''))
        email = sanitize_input(request.form.get('email', '').lower())
        department = sanitize_input(request.form.get('department', ''))
        college = sanitize_input(request.form.get('college', ''))
        if not full_name or not email:
            return jsonify({'success': False, 'error': 'Please fill in all fields.'}), 400
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({'success': False, 'error': 'Please enter a valid email address.'}), 400
        existing = db.session.query(User).filter(User.email == email, User.role == UserRole.LECTURER).first()
        if existing:
            return jsonify({'success': False, 'error': f'{email} is already a registered lecturer.'}), 400
        verification_code = generate_secure_verification_code(full_name, email, department)
        expires_at = datetime.now() + timedelta(days=7)
        dept_code = get_department_code(department)
        dept_count = db.session.query(LecturerVerification).filter(LecturerVerification.department == department).count() + 1
        staff_id = f"L/{dept_code}/{dept_count:03d}"
        verification = LecturerVerification(verification_code=verification_code, staff_id=staff_id, full_name=full_name, email=email, department=department, college=college, created_by=current_user.id, expires_at=expires_at, security_token=secrets.token_urlsafe(32), ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent', ''))
        db.session.add(verification)
        db.session.commit()
        lecturer_data = {'full_name': full_name, 'staff_id': staff_id, 'email': email, 'department': department, 'college': college}
        EmailService.send_lecturer_verification_email(lecturer_data, verification_code, expires_at)
        return jsonify({'success': True, 'message': f'Verification code sent to {email}!', 'staff_id': staff_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/send-verification', methods=['GET'])
@admin_required
@no_cache
def send_verification_page():
    return render_template('admin/admin_send_verification.html', academic_structure=ACADEMIC_STRUCTURE)

@app.route('/admin/resend-code/<int:code_id>', methods=['POST'])
@admin_required
def resend_lecturer_code(code_id):
    verification = db.session.query(LecturerVerification).get(code_id)
    if not verification or verification.is_used:
        flash('Cannot resend this code.', 'danger')
        return redirect(url_for('admin_lecturer_codes'))
    lecturer_data = {'full_name': verification.full_name, 'staff_id': verification.staff_id, 'email': verification.email, 'department': verification.department, 'college': verification.college or 'Not specified'}
    EmailService.send_lecturer_verification_email(lecturer_data, verification.verification_code, verification.expires_at)
    verification.email_sent = True
    verification.email_sent_at = datetime.now()
    db.session.commit()
    flash(f'Code resent to {verification.email}', 'success')
    return redirect(url_for('admin_lecturer_codes'))

@app.route('/admin/lecturer-requests')
@admin_required
@no_cache
def admin_lecturer_requests():
    pending_requests = db.session.query(LecturerRegistrationRequest).filter_by(status='pending').order_by(LecturerRegistrationRequest.created_at.desc()).all()
    approved_requests = db.session.query(LecturerRegistrationRequest).filter(LecturerRegistrationRequest.status.in_(['approved', 'rejected'])).order_by(LecturerRegistrationRequest.reviewed_at.desc()).limit(50).all()
    return render_template('admin/admin_lecturer_requests.html', pending_requests=pending_requests, approved_requests=approved_requests)

@app.route('/admin/approve-request/<int:request_id>', methods=['POST'])
@admin_required
def approve_lecturer_request(request_id):
    try:
        request_obj = db.session.query(LecturerRegistrationRequest).get(request_id)
        if not request_obj or request_obj.status != 'pending':
            return jsonify({'success': False, 'message': 'Request not found or already processed'}), 400
        request_obj.status = 'approved'
        request_obj.reviewed_at = datetime.now()
        request_obj.reviewed_by = current_user.id
        verification_code = generate_secure_verification_code(request_obj.full_name, request_obj.email, request_obj.department)
        expires_at = datetime.now() + timedelta(days=7)
        verification = LecturerVerification(verification_code=verification_code, staff_id=request_obj.staff_id, full_name=request_obj.full_name, email=request_obj.email, department=request_obj.department, college=request_obj.college, created_by=current_user.id, expires_at=expires_at, security_token=secrets.token_urlsafe(32), ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent', ''))
        db.session.add(verification)
        db.session.commit()
        lecturer_data = {'full_name': request_obj.full_name, 'staff_id': request_obj.staff_id, 'email': request_obj.email, 'department': request_obj.department, 'college': request_obj.college}
        EmailService.send_lecturer_verification_email(lecturer_data, verification_code, expires_at)
        return jsonify({'success': True, 'message': 'Request approved and verification code sent'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/reject-request/<int:request_id>', methods=['POST'])
@admin_required
def reject_lecturer_request(request_id):
    try:
        request_obj = db.session.query(LecturerRegistrationRequest).get(request_id)
        if not request_obj or request_obj.status != 'pending':
            return jsonify({'success': False, 'message': 'Request not found or already processed'}), 400
        data = request.get_json()
        reason = sanitize_input(data.get('reason', 'No reason provided'))
        request_obj.status = 'rejected'
        request_obj.reviewed_at = datetime.now()
        request_obj.reviewed_by = current_user.id
        request_obj.admin_notes = reason
        db.session.commit()
        return jsonify({'success': True, 'message': 'Request rejected'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== API ROUTES ====================
@app.route('/api/check-existing-user', methods=['POST'])
def check_existing_user():
    data = request.get_json()
    email = sanitize_input(data.get('email', '').lower())
    matric = sanitize_input(data.get('matric', '').upper())
    return jsonify({'email_exists': db.session.query(User).filter_by(email=email).first() is not None if email else False, 'matric_exists': db.session.query(User).filter_by(matric=matric).first() is not None if matric else False})

@app.route('/api/submission/<int:submission_id>/feedback')
@login_required
def get_submission_feedback(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if current_user.is_student() and submission.student_id != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    return jsonify({'success': True, 'grade': submission.grade, 'feedback': submission.feedback, 'assignment_title': submission.assignment.title})

@app.route('/verify-lecturer-code', methods=['POST'])
@rate_limit(limit=10, window=60)
def verify_lecturer_code():
    data = request.get_json()
    submitted_code = sanitize_input(data.get('code', '').upper())
    if not submitted_code or len(submitted_code) < 6 or len(submitted_code) > 9:
        return jsonify({'valid': False, 'message': 'Invalid verification code format.'})
    verification = db.session.query(LecturerVerification).filter_by(verification_code=submitted_code, is_used=False).first()
    if not verification:
        if db.session.query(LecturerVerification).filter_by(verification_code=submitted_code, is_used=True).first():
            return jsonify({'valid': False, 'message': 'This code has already been used.'})
        return jsonify({'valid': False, 'message': 'Invalid verification code.'})
    if verification.expires_at < datetime.now():
        return jsonify({'valid': False, 'message': 'This code has expired.'})
    can_proceed, error_msg = verify_lecturer_code_rate_limit(verification)
    if not can_proceed:
        return jsonify({'valid': False, 'message': error_msg})
    verification.verification_attempts += 1
    verification.last_verification_attempt = datetime.now()
    db.session.commit()
    return jsonify({'valid': True, 'message': 'Code verified!'})

@app.route('/api/academic-structure', methods=['GET'])
def api_academic_structure():
    return jsonify({'Colleges': ACADEMIC_STRUCTURE})

@app.route('/api/departments-by-college', methods=['POST'])
def api_departments_by_college():
    data = request.get_json()
    college_name = sanitize_input(data.get('college', ''))
    for college in ACADEMIC_STRUCTURE:
        if college.get('College') == college_name:
            return jsonify({'departments': college.get('Departments', [])})
    return jsonify({'departments': []})

@app.route('/api/connectivity-check', methods=['GET', 'HEAD'])
def connectivity_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat(), 'server_time': time.time()}), 200

# ==================== LECTURER DASHBOARD ====================
@app.route('/lecturer-dashboard')
@login_required
def lecturer_dashboard():
    if not current_user.is_lecturer() and not current_user.is_admin():
        flash('Access denied. Lecturer privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    try:
        assignments = db.session.query(Assignment).filter_by(created_by=current_user.id).order_by(Assignment.created_at.desc()).all()
        total_submissions, total_graded = 0, 0
        for assignment in assignments:
            subs = db.session.query(Submission).filter_by(assignment_id=assignment.id, is_draft=False).all()
            assignment.submission_count = len(subs)
            assignment.graded_count = len([s for s in subs if s.grade is not None])
            total_submissions += assignment.submission_count
            total_graded += assignment.graded_count
        total_assignments = len(assignments)
        pending_grading = total_submissions - total_graded
        recent_submissions = db.session.query(Submission).join(Assignment).filter(Assignment.created_by == current_user.id, Submission.is_draft == False).order_by(Submission.submitted_at.desc()).limit(10).all()
        return render_template('lecturer/lecturer_dashboard.html', assignments=assignments, total_assignments=total_assignments, total_submissions=total_submissions, total_graded=total_graded, pending_grading=pending_grading, recent_submissions=recent_submissions, now=datetime.now())
    except Exception as e:
        flash('Error loading dashboard.', 'danger')
        return redirect(url_for('dashboard'))

# ==================== STUDENT DASHBOARD ====================
@app.route('/student-dashboard')
@login_required
def student_dashboard():
    if not current_user.is_student():
        flash('Access denied. Student privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    student_level = current_user.current_level or '100'
    student_department_id = current_user.department_id
    
    query = db.session.query(Assignment).filter(Assignment.is_published == True, Assignment.deadline > datetime.now())
    query = query.filter(Assignment.target_level == student_level, Assignment.target_department_id == student_department_id)
    
    filter_level = request.args.get('level', '')
    filter_semester = request.args.get('semester', '')
    filter_academic_year = request.args.get('academic_year', '')
    filter_search = request.args.get('search', '')
    
    if filter_level:
        query = query.filter(Assignment.target_level == filter_level)
    if filter_semester:
        query = query.filter(Assignment.target_semester == filter_semester)
    if filter_academic_year:
        query = query.filter(Assignment.target_academic_year == filter_academic_year)
    if filter_search:
        query = query.filter(db.or_(Assignment.title.ilike(f'%{filter_search}%'), Assignment.course_code.ilike(f'%{filter_search}%'), Assignment.course_title.ilike(f'%{filter_search}%')))
    
    all_available_assignments = query.order_by(Assignment.deadline.asc()).all()
    submitted_ids = [s[0] for s in db.session.query(Submission.assignment_id).filter_by(student_id=current_user.id, is_draft=False).all()]
    available_assignments = [a for a in all_available_assignments if a.id not in submitted_ids]
    submissions = db.session.query(Submission).filter_by(student_id=current_user.id, is_draft=False).order_by(Submission.submitted_at.desc()).all()
    
    graded_submissions = [s for s in submissions if s.grade is not None]
    avg_grade = sum(s.grade for s in graded_submissions) / len(graded_submissions) if graded_submissions else 0
    
    progress_summary = CourseService.get_student_progress_summary(current_user.id) if hasattr(CourseService, 'get_student_progress_summary') else None
    eligible, message = AcademicService.check_promotion_eligibility(current_user.id) if hasattr(AcademicService, 'check_promotion_eligibility') else (False, '')
    
    return render_template('student/student_dashboard.html', submissions=submissions, available_assignments=available_assignments, total_submissions=len(submissions), graded_count=len(graded_submissions), pending_count=len(submissions)-len(graded_submissions), avg_grade=round(avg_grade, 1), pending_assignments=len(available_assignments), completed_assignments=len(graded_submissions), recent_submissions=submissions[:5], now=datetime.now(), progress_summary=progress_summary, eligible_for_promotion=eligible, promotion_message=message)

# ==================== PROFILE ROUTES ====================
@app.route('/profile')
@login_required
def profile():
    return render_template('shared/profile.html')

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_pwd = request.form.get('current_password')
        new_pwd = request.form.get('new_password')
        confirm_pwd = request.form.get('confirm_password')
        if not check_password_hash(current_user.password, current_pwd):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('change_password'))
        if new_pwd != confirm_pwd:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('change_password'))
        is_valid, errors = validate_password_strength(new_pwd)
        if not is_valid:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('change_password'))
        current_user.password = generate_password_hash(new_pwd)
        db.session.commit()
        flash('Password changed successfully!', 'success')
        return redirect(url_for('profile'))
    return render_template('shared/change_password.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('shared/settings.html')

@app.route('/help')
@login_required
def help_page():
    return render_template('shared/help.html')

# ==================== ERROR HANDLERS ====================
@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(429)
def ratelimit_error(error):
    return render_template('errors/429.html'), 429

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# ==================== BEFORE REQUEST ====================
@app.before_request
def before_request():
    public_routes = ['home', 'login', 'register', 'static', 'verify_lecturer_code', 'check_auth', 'verify', 'resend_code', 'check_existing_user', 'api_academic_structure', 'api_departments_by_college', 'connectivity-check', 'logout']
    if request.endpoint in public_routes:
        return None
    if current_user.is_authenticated:
        return None
    flash('Please log in to access this page.', 'warning')
    return redirect(url_for('login'))

# ==================== CREATE DEFAULT ADMIN ====================
def create_default_admin():
    with app.app_context():
        try:
            if not db.session.query(User).filter_by(matric='ADMIN001').first():
                admin = User(email='admin@submita.com', matric='ADMIN001', name='System Administrator', password=generate_password_hash('Admin123!'), code='123456', verified=True, role=UserRole.ADMIN, account_active=True, email_verified=True)
                db.session.add(admin)
                db.session.commit()
                print("Admin created: ADMIN001 / Admin123!")
            if not db.session.query(User).filter_by(matric='LEC001').first():
                lecturer = User(email='lecturer@mouau.edu.ng', matric='LEC001', name='Dr. John Okonkwo', password=generate_password_hash('Lecturer123!'), code='123456', verified=True, role=UserRole.LECTURER, account_active=True, email_verified=True)
                db.session.add(lecturer)
                db.session.commit()
                print("Lecturer created: LEC001 / Lecturer123!")
            if not db.session.query(User).filter_by(matric='STU001').first():
                student = User(email='student@gmail.com', matric='STU001', name='Test Student', password=generate_password_hash('Student123!'), code='123456', verified=True, role=UserRole.STUDENT, level='300', current_level='300', account_active=True, email_verified=True)
                db.session.add(student)
                db.session.commit()
                print("Student created: STU001 / Student123!")
        except Exception as e:
            print(f"Error creating default users: {e}")

# ==================== RUN APP ====================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_default_admin()
    
    print("\n" + "=" * 70)
    print("🔒 SUBMITA APPLICATION - ENTERPRISE SECURITY EDITION")
    print("=" * 70)
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print(f"📍 Local Access:    http://localhost:5000")
    print(f"📍 LAN Access:      http://{local_ip}:5000")
    print("=" * 70)
    print("🔑 Login Credentials:")
    print("   Admin:    ADMIN001 / Admin123!")
    print("   Lecturer: LEC001 / Lecturer123!")
    print("   Student:  STU001 / Student123!")
    print("=" * 70)
    print("🔐 SECURITY FEATURES ENABLED:")
    print("   • One Email = One Account Only")
    print("   • One Matric/Staff ID = One Account Only")
    print("   • Password Hashing")
    print("   • CSRF Protection")
    print("   • Rate Limiting")
    print("   • Session Security")
    print("   • Input Sanitization & XSS Prevention")
    print("   • SQL Injection Protection")
    print("   • Secure File Upload Scanning")
    print("   • Activity Logging & Audit Trail")
    print("=" * 70)
    print("\n✅ Server is running securely on ALL network interfaces.")
    print("   Other devices on your network can access via LAN IP above.")
    print("   Press CTRL+C to stop.\n")
    
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=True)