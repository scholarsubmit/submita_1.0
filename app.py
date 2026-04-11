from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session, send_file, make_response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from models import db, User, Assignment, AssignmentSubmission, Submission, ActivityLog, UserRole
from config import Config
import random
from difflib import SequenceMatcher
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from functools import wraps
import socket
import csv
import io
import json
from collections import Counter

# Create Flask app FIRST
app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static',
            template_folder='templates')

# Load config SECOND
app.config.from_object(Config)

# Initialize extensions THIRD
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
mail = Mail(app)   # This will now work because 'app' is defined

# Now continue with the rest of your app (upload folders, allowed_file, decorators, routes...)
# Configure upload folders
UPLOAD_FOLDER = 'uploads'
ASSIGNMENT_FOLDER = 'uploads/assignments'
SUBMISSION_FOLDER = 'uploads/submissions'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'py', 'js', 'java', 'cpp', 'c', 'zip', 'rar', 
                      'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ASSIGNMENT_FOLDER'] = ASSIGNMENT_FOLDER
app.config['SUBMISSION_FOLDER'] = SUBMISSION_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ASSIGNMENT_FOLDER, exist_ok=True)
os.makedirs(SUBMISSION_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Role-based access decorators
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash("Access denied. Admin privileges required.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def lecturer_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not (current_user.is_lecturer() or current_user.is_admin()):
            flash("Access denied. Lecturer privileges required.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def determine_role(email):
    """Automatically determine role based on email domain"""
    if email.endswith('@mouau.edu.ng'):
        return UserRole.LECTURER
    return UserRole.STUDENT

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

@app.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        elif current_user.is_lecturer():
            return redirect(url_for('lecturer_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return render_template('landing.html')

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        elif current_user.is_lecturer():
            return redirect(url_for('lecturer_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        matric = request.form['matric'].strip().upper()
        password = request.form['password']
        
        user = User.query.filter_by(matric=matric).first()
        
        if user and check_password_hash(user.password, password):
            if user.verified:
                login_user(user)
                user.last_login = datetime.utcnow()
                
                activity = ActivityLog(user_id=user.id, action="User logged in")
                db.session.add(activity)
                db.session.commit()
                
                flash(f"Welcome back, {user.name}!", "success")
                
                if user.is_admin():
                    return redirect(url_for('admin_dashboard'))
                elif user.is_lecturer():
                    return redirect(url_for('lecturer_dashboard'))
                else:
                    return redirect(url_for('student_dashboard'))
            else:
                flash("Please verify your email before logging in.", "warning")
                return redirect(url_for('verify', email=user.email))
        else:
            flash("Invalid matric number or password.", "danger")
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        matric = request.form['matric'].strip().upper()
        name = request.form['name'].strip()
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please login.", "warning")
            return redirect(url_for('login'))
        
        if User.query.filter_by(matric=matric).first():
            flash("Matric number already exists.", "danger")
            return redirect(url_for('register'))
        
        role = determine_role(email)
        code = str(random.randint(100000, 999999))
    
        user = User(
            email=email, 
            matric=matric, 
            name=name, 
            password=generate_password_hash(password), 
            code=code, 
            role=role,
            verified=False
        )
        db.session.add(user)
        db.session.commit()
        
        # Send verification email
        try:
            msg = Message('Verify Your Email - Submita', 
                         sender=app.config['MAIL_USERNAME'], 
                         recipients=[email])
            msg.body = f'''Welcome to Submita, {name}!

Your account has been created as a {role.upper()}.

Your verification code is: {code}

Enter this code to verify your email address.

If you didn't request this, please ignore this email.

Best regards,
Submita Team
2025/2026 Computer Science Department, MOUAU
'''
            mail.send(msg)
            flash(f"Verification code sent to {email}. Please check your inbox/spam folder.", "success")
        except Exception as e:
            app.logger.error(f"Email failed: {e}")
            print(f"Email sending error: {e}")
            flash(f"Could not send email. Please contact support.", "danger")

        return redirect(url_for('verify', email=email))
    
    return render_template('register.html')

@app.route('/verify/<email>', methods=['GET', 'POST'])
def verify(email):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('login'))
    
    if user.verified:
        flash("Email already verified. Please login.", "success")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        code = request.form['code']
        if user and user.code == code:
            user.verified = True
            db.session.commit()
            
            activity = ActivityLog(user_id=user.id, action="Email verified")
            db.session.add(activity)
            db.session.commit()
            
            flash("Email verified successfully! Please login.", "success")
            return redirect(url_for('login'))
        else:
            flash("Invalid verification code.", "danger")
    
    return render_template('verify.html', email=email)

@app.route('/resend-code/<email>')
def resend_code(email):
    user = User.query.filter_by(email=email).first()
    if user and not user.verified:
        code = str(random.randint(100000, 999999))
        user.code = code
        db.session.commit()
        
        try:
            msg = Message('New Verification Code - Submita', 
                         sender=app.config['MAIL_USERNAME'], 
                         recipients=[email])
            msg.body = f'Your new verification code is: {code}'
            mail.send(msg)
            flash("New verification code sent!", "success")
        except Exception as e:
            print(f"Email error: {e}")
            flash(f"Could not send email. Your code is: {code} (check console)", "info")
            print(f"\nNEW CODE FOR {email}: {code}\n")
    
    return redirect(url_for('verify', email=email))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if user:
            reset_code = str(random.randint(100000, 999999))
            user.code = reset_code
            db.session.commit()
            
            try:
                msg = Message('Password Reset Code - Submita', 
                             sender=app.config['MAIL_USERNAME'], 
                             recipients=[email])
                msg.body = f'''Hello {user.name},

Your password reset code is: {reset_code}

Enter this code to reset your password.

Best regards,
Submita Team
'''
                mail.send(msg)
                flash("Password reset code sent to your email!", "success")
            except Exception as e:
                print(f"Email error: {e}")
                flash(f"Reset code: {reset_code} (check console)", "info")
                print(f"\nRESET CODE FOR {email}: {reset_code}\n")
            return redirect(url_for('reset_password', email=email))
        else:
            flash("Email address not found.", "danger")
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<email>', methods=['GET', 'POST'])
def reset_password(email):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Invalid request.", "danger")
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        code = request.form['code']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('reset_password', email=email))
        
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for('reset_password', email=email))
        
        if user.code == code:
            user.password = generate_password_hash(password)
            user.code = None
            db.session.commit()
            
            flash("Password reset successful! Please login.", "success")
            return redirect(url_for('login'))
        else:
            flash("Invalid reset code.", "danger")
    
    return render_template('reset_password.html', email=email)

# ==================== DASHBOARD ROUTES ====================

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    elif current_user.is_lecturer():
        return redirect(url_for('lecturer_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

@app.route('/student-dashboard')
@login_required
def student_dashboard():
    if not current_user.is_student():
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))
    
    now = datetime.utcnow()
    submissions = Submission.query.filter_by(student_id=current_user.id).order_by(Submission.submitted_at.desc()).all()
    
    submitted_ids = [s.assignment_id for s in submissions]
    if submitted_ids:
        available_assignments = AssignmentSubmission.query.filter(
            AssignmentSubmission.deadline > now,
            ~AssignmentSubmission.id.in_(submitted_ids)
        ).order_by(AssignmentSubmission.deadline.asc()).all()
    else:
        available_assignments = AssignmentSubmission.query.filter(
            AssignmentSubmission.deadline > now
        ).order_by(AssignmentSubmission.deadline.asc()).all()
    
    past_assignments = AssignmentSubmission.query.filter(
        AssignmentSubmission.deadline <= now
    ).order_by(AssignmentSubmission.deadline.desc()).all()
    
    return render_template('student_dashboard.html', 
                         user=current_user,
                         submissions=submissions,
                         available_assignments=available_assignments,
                         past_assignments=past_assignments,
                         now=now)

@app.route('/profile')
@login_required
def profile():
    """Display user profile information"""
    user = current_user
    return render_template('profile.html', user=user)

@app.route('/lecturer-dashboard')
@login_required
def lecturer_dashboard():
    if not current_user.is_lecturer():
        flash("Access denied. Lecturer privileges required.", "danger")
        return redirect(url_for('dashboard'))
    
    now = datetime.utcnow()
    assignments = AssignmentSubmission.query.filter_by(created_by=current_user.id).order_by(AssignmentSubmission.created_at.desc()).all()
    
    assignment_ids = [a.id for a in assignments]
    if assignment_ids:
        submissions = Submission.query.filter(Submission.assignment_id.in_(assignment_ids)).order_by(Submission.submitted_at.desc()).all()
    else:
        submissions = []
    
    total_students = User.query.filter_by(role='student').count()
    total_submissions = len(submissions)
    pending_grades = len([s for s in submissions if s.grade is None])
    
    graded_submissions = [s for s in submissions if s.grade is not None]
    avg_grade = sum(s.grade for s in graded_submissions) / len(graded_submissions) if graded_submissions else 0
    
    return render_template('lecturer_dashboard.html',
                         user=current_user,
                         assignments=assignments,
                         submissions=submissions,
                         total_students=total_students,
                         total_submissions=total_submissions,
                         pending_grades=pending_grades,
                         avg_grade=round(avg_grade, 1),
                         now=now)

# ==================== ASSIGNMENT MANAGEMENT ====================

@app.route('/create-assignment', methods=['GET', 'POST'])
@lecturer_required
def create_assignment():
    if request.method == 'POST':
        course_title = request.form['course_title']
        course_code = request.form['course_code'].upper()
        title = request.form['title']
        deadline_str = request.form['deadline']
        questions = request.form['questions']
        instructions = request.form.get('instructions', '')
        
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        
        attachment_path = None
        attachment_filename = None
        attachment_type = None
        
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                filepath = os.path.join(app.config['ASSIGNMENT_FOLDER'], filename)
                file.save(filepath)
                attachment_path = filename
                attachment_filename = file.filename
                attachment_type = file.filename.rsplit('.', 1)[1].lower()
        
        assignment = AssignmentSubmission(
            course_title=course_title,
            course_code=course_code,
            title=title,
            deadline=deadline,
            questions=questions,
            instructions=instructions,
            attachment_path=attachment_path,
            attachment_filename=attachment_filename,
            attachment_type=attachment_type,
            created_by=current_user.id
        )
        db.session.add(assignment)
        db.session.commit()
        
        activity = ActivityLog(user_id=current_user.id, action="Created assignment", details=title)
        db.session.add(activity)
        db.session.commit()
        
        flash(f"Assignment '{title}' created successfully!", "success")
        return redirect(url_for('lecturer_dashboard'))
    
    return render_template('create_assignment.html')

@app.route('/assignment/<int:assignment_id>/manage')
@lecturer_required
def manage_assignment(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash("Permission denied.", "danger")
        return redirect(url_for('lecturer_dashboard'))
    
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    students = User.query.filter_by(role='student').all()
    
    total_students = len(students)
    submitted_count = len(submissions)
    pending_count = total_students - submitted_count
    graded_count = len([s for s in submissions if s.grade is not None])
    avg_grade = sum(s.grade for s in submissions if s.grade) / graded_count if graded_count > 0 else 0
    plagiarism_alerts = [s for s in submissions if s.plagiarism_score > 30]
    
    # Add current datetime
    now = datetime.utcnow()
    
    return render_template('manage_assignment.html',
                         assignment=assignment,
                         submissions=submissions,
                         students=students,
                         total_students=total_students,
                         submitted_count=submitted_count,
                         pending_count=pending_count,
                         graded_count=graded_count,
                         avg_grade=round(avg_grade, 1),
                         plagiarism_alerts=plagiarism_alerts,
                         now=now)   # <-- add this

@app.route('/assignment/<int:assignment_id>/edit', methods=['GET', 'POST'])
@lecturer_required
def edit_assignment(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash("Permission denied.", "danger")
        return redirect(url_for('lecturer_dashboard'))
    
    if request.method == 'POST':
        assignment.course_title = request.form['course_title']
        assignment.course_code = request.form['course_code'].upper()
        assignment.title = request.form['title']
        assignment.questions = request.form['questions']
        assignment.instructions = request.form.get('instructions', '')
        assignment.deadline = datetime.strptime(request.form['deadline'], '%Y-%m-%dT%H:%M')
        
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename and allowed_file(file.filename):
                if assignment.attachment_path:
                    old_path = os.path.join(app.config['ASSIGNMENT_FOLDER'], assignment.attachment_path)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                filepath = os.path.join(app.config['ASSIGNMENT_FOLDER'], filename)
                file.save(filepath)
                assignment.attachment_path = filename
                assignment.attachment_filename = file.filename
                assignment.attachment_type = file.filename.rsplit('.', 1)[1].lower()
        
        db.session.commit()
        flash("Assignment updated successfully!", "success")
        return redirect(url_for('manage_assignment', assignment_id=assignment.id))
    
    return render_template('edit_assignment.html', assignment=assignment)

@app.route('/assignment/<int:assignment_id>/void', methods=['POST'])
@lecturer_required
def void_assignment(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash("Permission denied.", "danger")
        return redirect(url_for('lecturer_dashboard'))
    
    db.session.delete(assignment)
    db.session.commit()
    flash(f"Assignment '{assignment.title}' has been voided.", "success")
    return redirect(url_for('lecturer_dashboard'))

@app.route('/assignment/<int:assignment_id>/view')
@login_required
def view_assignment(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    submission = None
    if current_user.is_student():
        submission = Submission.query.filter_by(assignment_id=assignment_id, student_id=current_user.id).first()
    now = datetime.utcnow()  # Add this line
    return render_template('view_assignment.html', assignment=assignment, submission=submission, now=now)
@app.route('/assignment/<int:assignment_id>/remove-attachment', methods=['POST'])
@lecturer_required
def remove_assignment_attachment(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    if assignment.created_by != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Permission denied'}), 403
    if assignment.attachment_path:
        path = os.path.join(app.config['ASSIGNMENT_FOLDER'], assignment.attachment_path)
        if os.path.exists(path):
            os.remove(path)
        assignment.attachment_path = None
        assignment.attachment_filename = None
        assignment.attachment_type = None
        db.session.commit()
    return jsonify({'success': True})

# ==================== SUBMISSION MANAGEMENT ====================

@app.route('/submit/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def submit_assignment(assignment_id):
    if not current_user.is_student():
        flash("Only students can submit assignments.", "danger")
        return redirect(url_for('dashboard'))
    
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    if assignment.deadline < datetime.utcnow():
        flash("Deadline has passed. You cannot submit.", "danger")
        return redirect(url_for('student_dashboard'))
    
    existing = Submission.query.filter_by(assignment_id=assignment_id, student_id=current_user.id).first()
    if existing:
        flash("You have already submitted this assignment.", "warning")
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        github_url = request.form.get('github_url', '')
        file = request.files.get('file')
        
        filename = None
        original_filename = None
        file_type = None
        if file and file.filename and allowed_file(file.filename):
            original_filename = file.filename
            file_type = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{current_user.id}_{assignment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['SUBMISSION_FOLDER'], filename)
            file.save(filepath)
        
        all_submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
        plagiarism_detected = False
        highest_score = 0
        for sub in all_submissions:
            if sub.content and content:
                similarity = SequenceMatcher(None, content, sub.content).ratio()
                if similarity > highest_score:
                    highest_score = similarity
                if similarity > 0.7:
                    plagiarism_detected = True
        plagiarism_score = highest_score * 100
        
        submission = Submission(
            assignment_id=assignment_id,
            student_id=current_user.id,
            content=content,
            file_path=filename,
            original_filename=original_filename,
            file_type=file_type,
            github_url=github_url,
            plagiarism_score=plagiarism_score
        )
        db.session.add(submission)
        db.session.commit()
        
        activity = ActivityLog(user_id=current_user.id, action="Submitted assignment", details=f"Assignment: {assignment.title}")
        db.session.add(activity)
        db.session.commit()
        
        if plagiarism_detected:
            flash(f"⚠️ Warning: Potential plagiarism detected! Similarity: {plagiarism_score:.1f}%", "danger")
        else:
            flash(f"✓ Assignment submitted successfully! Plagiarism score: {plagiarism_score:.1f}%", "success")
        return redirect(url_for('student_dashboard'))
    
    return render_template('submit.html', assignment=assignment)

@app.route('/grade/<int:submission_id>', methods=['GET', 'POST'])
@lecturer_required
def grade_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    assignment = AssignmentSubmission.query.get(submission.assignment_id)
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash("Permission denied.", "danger")
        return redirect(url_for('lecturer_dashboard'))
    
    if request.method == 'POST':
        grade = float(request.form['grade'])
        feedback = request.form['feedback']
        submission.grade = grade
        submission.feedback = feedback
        db.session.commit()
        flash(f"Grade submitted for {submission.student.name}!", "success")
        return redirect(url_for('manage_assignment', assignment_id=assignment.id))
    
    return render_template('grade_submission.html', submission=submission, assignment=assignment)

@app.route('/submission/<int:submission_id>/resubmit', methods=['POST'])
@login_required
def resubmit_assignment(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    assignment = AssignmentSubmission.query.get(submission.assignment_id)
    if submission.student_id != current_user.id:
        flash("You can only resubmit your own assignments.", "danger")
        return redirect(url_for('student_dashboard'))
    if assignment.deadline < datetime.utcnow():
        flash("Cannot resubmit after deadline.", "danger")
        return redirect(url_for('student_dashboard'))
    
    # Delete old file
    if submission.file_path:
        old_path = os.path.join(app.config['SUBMISSION_FOLDER'], submission.file_path)
        if os.path.exists(old_path):
            os.remove(old_path)
    db.session.delete(submission)
    db.session.commit()
    flash("Previous submission removed. You can now submit again.", "info")
    return redirect(url_for('submit_assignment', assignment_id=assignment.id))

# ==================== BULK OPERATIONS ====================

@app.route('/assignment/<int:assignment_id>/bulk-grade', methods=['POST'])
@lecturer_required
def bulk_grade(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash("Permission denied.", "danger")
        return redirect(url_for('lecturer_dashboard'))
    
    submission_ids = request.form.getlist('submission_ids[]')
    grades = request.form.getlist('grades[]')
    for submission_id, grade in zip(submission_ids, grades):
        if grade:
            sub = Submission.query.get(submission_id)
            if sub:
                sub.grade = float(grade)
    db.session.commit()
    flash("Bulk grading completed!", "success")
    return redirect(url_for('manage_assignment', assignment_id=assignment_id))

@app.route('/assignment/<int:assignment_id>/export/csv')
@lecturer_required
def export_submissions_csv(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Matric Number', 'Student Name', 'Email', 'Submission Date', 'Plagiarism Score', 'Grade', 'Feedback', 'Has File'])
    for sub in submissions:
        writer.writerow([
            sub.student.matric, sub.student.name, sub.student.email,
            sub.submitted_at.strftime('%Y-%m-%d %H:%M:%S'),
            f"{sub.plagiarism_score:.1f}%",
            f"{sub.grade:.1f}%" if sub.grade else 'Not Graded',
            sub.feedback or '',
            'Yes' if sub.file_path else 'No'
        ])
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={assignment.course_code}_{assignment.title}_submissions.csv'
    return response

@app.route('/assignment/<int:assignment_id>/export/excel')
@lecturer_required
def export_submissions_excel(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    
    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Submissions"
    
    # Headers
    headers = ['Matric Number', 'Student Name', 'Email', 'Submission Date', 'Plagiarism Score', 'Grade', 'Feedback', 'Has File']
    ws.append(headers)
    
    # Data rows
    for sub in submissions:
        ws.append([
            sub.student.matric,
            sub.student.name,
            sub.student.email,
            sub.submitted_at.strftime('%Y-%m-%d %H:%M:%S'),
            f"{sub.plagiarism_score:.1f}%",
            f"{sub.grade:.1f}%" if sub.grade else 'Not Graded',
            sub.feedback or '',
            'Yes' if sub.file_path else 'No'
        ])
    
    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(output, as_attachment=True, download_name=f"{assignment.course_code}_{assignment.title}_submissions.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ==================== PLAGIARISM ====================

@app.route('/assignment/<int:assignment_id>/plagiarism-report')
@lecturer_required
def plagiarism_report(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    similar_pairs = []
    for i, sub1 in enumerate(submissions):
        for sub2 in submissions[i+1:]:
            if sub1.content and sub2.content:
                sim = SequenceMatcher(None, sub1.content, sub2.content).ratio()
                if sim > 0.5:
                    similar_pairs.append({'student1': sub1.student.name, 'student2': sub2.student.name, 'similarity': sim*100})
    return render_template('plagiarism_report.html', assignment=assignment, submissions=submissions, similar_pairs=similar_pairs)

@app.route('/assignment/<int:assignment_id>/check-plagiarism', methods=['POST'])
@lecturer_required
def check_plagiarism(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    for sub in submissions:
        highest = 0
        for other in submissions:
            if other.id != sub.id and other.content and sub.content:
                sim = SequenceMatcher(None, sub.content, other.content).ratio()
                if sim > highest:
                    highest = sim
        sub.plagiarism_score = highest * 100
        db.session.commit()
    flash("Plagiarism check completed!", "success")
    return redirect(url_for('manage_assignment', assignment_id=assignment_id))

# ==================== FILE DOWNLOADS ====================

@app.route('/download/assignment/<int:assignment_id>')
@login_required
def download_assignment_file(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    if not assignment.attachment_path:
        flash("No file attached.", "warning")
        return redirect(request.referrer or url_for('dashboard'))
    filepath = os.path.join(app.config['ASSIGNMENT_FOLDER'], assignment.attachment_path)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=assignment.attachment_filename)
    flash("File not found.", "danger")
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/download/submission/<int:submission_id>')
@login_required
def download_submission_file(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    assignment = AssignmentSubmission.query.get(submission.assignment_id)
    if current_user.is_student() and submission.student_id != current_user.id:
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))
    if current_user.is_lecturer() and assignment.created_by != current_user.id:
        flash("Access denied.", "danger")
        return redirect(url_for('lecturer_dashboard'))
    if not submission.file_path:
        flash("No file attached.", "warning")
        return redirect(request.referrer or url_for('dashboard'))
    filepath = os.path.join(app.config['SUBMISSION_FOLDER'], submission.file_path)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=submission.original_filename)
    flash("File not found.", "danger")
    return redirect(request.referrer or url_for('dashboard'))

# ==================== ADMIN ROUTES ====================

@app.route('/admin-dashboard')
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_students = User.query.filter_by(role='student').count()
    total_lecturers = User.query.filter_by(role='lecturer').count()
    total_admins = User.query.filter_by(role='admin').count()
    total_submissions = Submission.query.count()
    total_assignments = AssignmentSubmission.query.count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(20).all()
    return render_template('admin_dashboard.html', 
                         total_users=total_users, total_students=total_students,
                         total_lecturers=total_lecturers, total_admins=total_admins,
                         total_submissions=total_submissions, total_assignments=total_assignments,
                         recent_users=recent_users, recent_activities=recent_activities)

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/change-role/<int:user_id>', methods=['POST'])
@admin_required
def change_user_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    if new_role in ['student', 'lecturer', 'admin']:
        old_role = user.role
        user.role = new_role
        db.session.commit()
        flash(f"Role of {user.name} changed to {new_role.upper()}", "success")
    else:
        flash("Invalid role.", "danger")
    return redirect(url_for('admin_users'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for('admin_users'))
    email = user.email
    db.session.delete(user)
    db.session.commit()
    flash(f"User {email} deleted.", "success")
    return redirect(url_for('admin_users'))

@app.route('/admin/filter')
@admin_required
def admin_filter():
    filter_type = request.args.get('type', 'all')
    from datetime import datetime

    if filter_type == 'all':
        # Return recent users and activities (same as initial load)
        recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
        recent_activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(20).all()
        return jsonify({
            'recent_users': [{'name': u.name, 'email': u.email, 'matric': u.matric, 'role': u.role, 'created_at': u.created_at.strftime('%Y-%m-%d')} for u in recent_users],
            'recent_activities': [{'action': a.action, 'user_name': a.user.name if a.user else 'System', 'timestamp': a.timestamp.strftime('%Y-%m-%d %H:%M')} for a in recent_activities]
        })
    elif filter_type in ['students', 'lecturers', 'admins']:
        role_map = {'students': 'student', 'lecturers': 'lecturer', 'admins': 'admin'}
        users = User.query.filter_by(role=role_map[filter_type]).order_by(User.created_at.desc()).all()
        return jsonify({
            'users': [{'name': u.name, 'email': u.email, 'matric': u.matric, 'role': u.role, 'created_at': u.created_at.strftime('%Y-%m-%d')} for u in users]
        })
    elif filter_type == 'submissions':
        submissions = Submission.query.order_by(Submission.submitted_at.desc()).limit(50).all()
        return jsonify({
            'submissions': [{
                'student_name': s.student.name,
                'assignment_title': s.assignment.title,
                'submitted_at': s.submitted_at.strftime('%Y-%m-%d %H:%M'),
                'plagiarism_score': round(s.plagiarism_score, 1),
                'grade': s.grade
            } for s in submissions]
        })
    elif filter_type == 'assignments':
        assignments = AssignmentSubmission.query.order_by(AssignmentSubmission.created_at.desc()).limit(50).all()
        return jsonify({
            'assignments': [{
                'title': a.title,
                'course_code': a.course_code,
                'deadline': a.deadline.strftime('%Y-%m-%d %H:%M'),
                'creator_name': User.query.get(a.created_by).name,
                'submission_count': Submission.query.filter_by(assignment_id=a.id).count()
            } for a in assignments]
        })
    else:
        return jsonify({'error': 'Invalid filter'}), 400
# ==================== API ====================

@app.route('/api/analytics')
@login_required
def get_analytics():
    if current_user.is_lecturer():
        submissions = Submission.query.filter(
            Submission.assignment_id.in_(
                db.session.query(AssignmentSubmission.id).filter_by(created_by=current_user.id)
            )
        ).all()
        total = len(submissions)
        avg_grade = sum(s.grade or 0 for s in submissions) / total if total else 0
        alerts = len([s for s in submissions if s.plagiarism_score > 30])
        return jsonify({'total_submissions': total, 'average_grade': round(avg_grade,2), 'plagiarism_alerts': alerts})
    return jsonify({})

@app.route('/api/submission/<int:submission_id>/feedback')
@login_required
def get_submission_feedback(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if current_user.is_student() and submission.student_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'grade': submission.grade, 'feedback': submission.feedback, 'plagiarism_score': submission.plagiarism_score})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create default admin if none exists
        if not User.query.filter_by(role='admin').first():
            # ... your admin creation code ...
        # ... other test accounts ...
    
    # ✅ PORT BINDING FOR CLOUD DEPLOYMENT
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)




