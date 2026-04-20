from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    jsonify,
    session,
    send_file,
    make_response,
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from flask_mail import Mail, Message
from flask_migrate import Migrate
from models import (
    db,
    User,
    Assignment,
    AssignmentSubmission,
    Submission,
    ActivityLog,
    UserRole,
    VerificationCode,
)
from config import Config
import random
import re
from difflib import SequenceMatcher
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
from functools import wraps
import os
import socket
import csv
import io
import json
from collections import Counter

def get_current_time():
    """Return a naive datetime for consistent comparison throughout the app"""
    return datetime.now()

def make_naive(dt):
    """Convert timezone-aware datetime to naive if needed"""
    if dt is None:
        return dt
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt

# Create Flask app
app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static",
    template_folder="templates",
)

# Load config
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"
mail = Mail(app)

# Configure upload folders
UPLOAD_FOLDER = "uploads"
ASSIGNMENT_FOLDER = "uploads/assignments"
SUBMISSION_FOLDER = "uploads/submissions"
ALLOWED_EXTENSIONS = {
    "txt", "pdf", "py", "js", "java", "cpp", "c", "zip", "rar",
    "doc", "docx", "xls", "xlsx", "ppt", "pptx", "jpg", "jpeg", "png", "gif",
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["ASSIGNMENT_FOLDER"] = ASSIGNMENT_FOLDER
app.config["SUBMISSION_FOLDER"] = SUBMISSION_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ASSIGNMENT_FOLDER, exist_ok=True)
os.makedirs(SUBMISSION_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash("Access denied. Admin privileges required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function


def lecturer_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not (current_user.is_lecturer() or current_user.is_admin()):
            flash("Access denied. Lecturer privileges required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def determine_role(email):
    if email.endswith("@mouau.edu.ng"):
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


def calculate_auto_grade(submission, assignment):
    breakdown = {}
    total_score = 0

    quality_score = 0
    if submission.content:
        code = submission.content
        has_functions = len(re.findall(r"def\s+\w+\s*\(", code)) > 0
        has_classes = len(re.findall(r"class\s+\w+", code)) > 0
        has_comments = len(re.findall(r"#.*$|//.*$", code, re.MULTILINE)) > 5
        code_length = len(code.split("\n"))

        if has_functions or has_classes:
            quality_score += 15
        if has_comments:
            quality_score += 10
        if 20 <= code_length <= 500:
            quality_score += 5

        quality_score = min(quality_score, 30)
        breakdown["code_quality"] = quality_score
        total_score += quality_score

    test_score = 0
    if hasattr(assignment, "test_cases") and assignment.test_cases:
        passed_tests = 0
        total_tests = len(assignment.test_cases)
        for test in assignment.test_cases:
            if submission.content and test.get("expected") in submission.content:
                passed_tests += 1
        if total_tests > 0:
            test_score = (passed_tests / total_tests) * 50
        breakdown["test_cases"] = round(test_score, 1)
        total_score += test_score

    plagiarism_penalty = 0
    if submission.plagiarism_score > 70:
        plagiarism_penalty = 30
    elif submission.plagiarism_score > 50:
        plagiarism_penalty = 20
    elif submission.plagiarism_score > 30:
        plagiarism_penalty = 10
    elif submission.plagiarism_score > 15:
        plagiarism_penalty = 5
    breakdown["plagiarism_penalty"] = plagiarism_penalty
    total_score -= plagiarism_penalty

    completeness_bonus = 0
    if submission.file_path:
        completeness_bonus = 10
    elif submission.content and len(submission.content) > 500:
        completeness_bonus = 5
    breakdown["completeness"] = completeness_bonus
    total_score += completeness_bonus

    final_grade = max(0, min(100, total_score))
    breakdown["final_grade"] = round(final_grade, 1)

    return final_grade, breakdown


# ==================== HOME ROUTE ====================

@app.route("/")
def home():
    return render_template("landing.html")


@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin():
        return redirect(url_for("admin_dashboard"))
    elif current_user.is_lecturer():
        return redirect(url_for("lecturer_dashboard"))
    else:
        return redirect(url_for("student_dashboard"))


# ==================== AUTHENTICATION ROUTES ====================

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        matric = request.form["matric"].strip().upper()
        password = request.form["password"]

        user = User.query.filter_by(matric=matric).first()

        if user and check_password_hash(user.password, password):
            if user.verified:
                login_user(user)
                user.last_login = get_current_time()

                activity = ActivityLog(user_id=user.id, action="User logged in")
                db.session.add(activity)
                db.session.commit()

                if user.is_admin():
                    return redirect(url_for("admin_dashboard"))
                elif user.is_lecturer():
                    return redirect(url_for("lecturer_dashboard"))
                else:
                    return redirect(url_for("student_dashboard"))
            else:
                flash("Please verify your email before logging in.", "warning")
                return redirect(url_for("verify", email=user.email))
        else:
            flash("Invalid matric number or password.", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        matric = request.form["matric"].strip().upper()
        name = request.form["name"].strip()
        password = request.form["password"]
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please login.", "warning")
            return redirect(url_for("login"))

        if User.query.filter_by(matric=matric).first():
            flash("Matric number already exists.", "danger")
            return redirect(url_for("register"))

        role = determine_role(email)
        code = str(random.randint(100000, 999999))

        user = User(
            email=email,
            matric=matric,
            name=name,
            password=generate_password_hash(password),
            code=code,
            role=role,
            verified=False,
        )
        db.session.add(user)
        db.session.commit()

        try:
            msg = Message(
                "Verify Your Email - Submita",
                sender=app.config["MAIL_USERNAME"],
                recipients=[email],
            )
            msg.body = f"""Welcome to Submita, {name}!

Your account has been created as a {role.upper()}.

Your verification code is: {code}

Click the link below to verify your email:
{url_for('verify', email=email, _external=True)}

Or enter this code on the verification page.

Best regards,
Submita Team
"""
            mail.send(msg)
            flash(f"Verification code sent to {email}. Please check your email.", "success")
        except Exception as e:
            app.logger.error(f"Email failed: {e}")
            print(f"Email error: {e}")
            flash(f"Verification code: {code} (Please save this code)", "info")

        session['verification_email'] = email
        return redirect(url_for("verify"))

    return render_template("register.html")


@app.route("/verify", methods=["GET", "POST"])
@app.route("/verify/<email>", methods=["GET", "POST"])
def verify(email=None):
    """Email verification page"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    
    if not email:
        email = session.get('verification_email') or request.args.get('email')
    
    if not email:
        flash("No verification pending. Please register first.", "warning")
        return redirect(url_for("register"))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("register"))
    
    if user.verified:
        flash("Email already verified. Please login.", "success")
        session.pop('verification_email', None)
        return redirect(url_for("login"))
    
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        
        if user.code == code:
            user.verified = True
            user.code = None
            db.session.commit()
            
            activity = ActivityLog(user_id=user.id, action="Email verified")
            db.session.add(activity)
            db.session.commit()
            
            session.pop('verification_email', None)
            flash("Email verified successfully! Please login.", "success")
            return redirect(url_for("login"))
        else:
            flash("Invalid verification code. Please try again.", "danger")
    
    return render_template("verify.html", email=email)


@app.route("/resend-code/<email>")
def resend_code(email):
    user = User.query.filter_by(email=email).first()
    if user and not user.verified:
        code = str(random.randint(100000, 999999))
        user.code = code
        db.session.commit()
        
        try:
            msg = Message(
                "New Verification Code - Submita",
                sender=app.config["MAIL_USERNAME"],
                recipients=[email],
            )
            msg.body = f"Your new verification code is: {code}"
            mail.send(msg)
            flash("New verification code sent! Please check your email.", "success")
        except Exception as e:
            print(f"Email error: {e}")
            flash(f"Verification code: {code}", "info")
        
        session['verification_email'] = email
    
    return redirect(url_for("verify"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            reset_code = str(random.randint(100000, 999999))
            user.code = reset_code
            db.session.commit()

            try:
                msg = Message(
                    "Password Reset Code - Submita",
                    sender=app.config["MAIL_USERNAME"],
                    recipients=[email],
                )
                msg.body = f"Your password reset code is: {reset_code}"
                mail.send(msg)
                flash("Password reset code sent!", "success")
            except Exception as e:
                print(f"Email error: {e}")
                flash(f"Reset code: {reset_code}", "info")
            return redirect(url_for("reset_password", email=email))
        else:
            flash("Email address not found.", "danger")

    return render_template("forgot_password.html")


@app.route("/reset-password/<email>", methods=["GET", "POST"])
def reset_password(email):
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Invalid request.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        code = request.form["code"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("reset_password", email=email))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("reset_password", email=email))

        if user.code == code:
            user.password = generate_password_hash(password)
            user.code = None
            db.session.commit()

            flash("Password reset successful! Please login.", "success")
            return redirect(url_for("login"))
        else:
            flash("Invalid reset code.", "danger")

    return render_template("reset_password.html", email=email)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


# ==================== DASHBOARD ROUTES ====================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        
        if name:
            current_user.name = name
        if email and email != current_user.email:
            if User.query.filter_by(email=email).first():
                flash("Email already taken.", "danger")
            else:
                current_user.email = email
                flash("Email updated successfully.", "success")
        
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))
    
    return render_template("profile.html", user=current_user)


@app.route("/student-dashboard")
@login_required
def student_dashboard():
    if not current_user.is_student():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    now = get_current_time()
    
    # Get final submissions (not drafts)
    submissions = (
        Submission.query.filter_by(student_id=current_user.id, is_draft=False)
        .order_by(Submission.submitted_at.desc())
        .all()
    )
    
    # Get drafts
    drafts = (
        Submission.query.filter_by(student_id=current_user.id, is_draft=True)
        .order_by(Submission.draft_saved_at.desc())
        .all()
    )

    submitted_ids = [s.assignment_id for s in submissions]
    if submitted_ids:
        available_assignments = (
            AssignmentSubmission.query.filter(
                AssignmentSubmission.deadline > now,
                ~AssignmentSubmission.id.in_(submitted_ids),
            )
            .order_by(AssignmentSubmission.deadline.asc())
            .all()
        )
    else:
        available_assignments = (
            AssignmentSubmission.query.filter(AssignmentSubmission.deadline > now)
            .order_by(AssignmentSubmission.deadline.asc())
            .all()
        )

    past_assignments = (
        AssignmentSubmission.query.filter(AssignmentSubmission.deadline <= now)
        .order_by(AssignmentSubmission.deadline.desc())
        .all()
    )

    graded_submissions = [s for s in submissions if s.grade is not None]
    avg_grade = (
        sum(s.grade for s in graded_submissions) / len(graded_submissions)
        if graded_submissions
        else 0
    )

    return render_template(
        "student_dashboard.html",
        user=current_user,
        submissions=submissions,
        drafts=drafts,
        available_assignments=available_assignments,
        past_assignments=past_assignments,
        now=now,
        avg_grade=round(avg_grade, 1),
    )


# ==================== LECTURER ROUTES ====================

@app.route("/lecturer-dashboard")
@login_required
def lecturer_dashboard():
    if not current_user.is_lecturer():
        flash("Access denied. Lecturer privileges required.", "danger")
        return redirect(url_for("dashboard"))

    now = get_current_time()

    assignments = (
        AssignmentSubmission.query.filter_by(created_by=current_user.id)
        .order_by(AssignmentSubmission.created_at.desc())
        .all()
    )

    total_submissions = 0
    total_graded = 0
    total_pending = 0
    total_flagged = 0
    
    for assignment in assignments:
        assignment_submissions = Submission.query.filter_by(assignment_id=assignment.id, is_draft=False).all()
        
        assignment.submission_count = len(assignment_submissions)
        assignment.graded_count = len([s for s in assignment_submissions if s.grade is not None])
        assignment.pending_count = assignment.submission_count - assignment.graded_count
        assignment.flagged_count = len([s for s in assignment_submissions if s.plagiarism_score > 30])
        
        total_submissions += assignment.submission_count
        total_graded += assignment.graded_count
        total_pending += assignment.pending_count
        total_flagged += assignment.flagged_count

    assignment_ids = [a.id for a in assignments]
    if assignment_ids:
        all_submissions = (
            Submission.query.filter(Submission.assignment_id.in_(assignment_ids), Submission.is_draft == False)
            .order_by(Submission.submitted_at.desc())
            .all()
        )
    else:
        all_submissions = []

    graded_subs = [s for s in all_submissions if s.grade is not None]
    avg_grade = sum(s.grade for s in graded_subs) / len(graded_subs) if graded_subs else 0

    return render_template(
        "lecturer_dashboard.html",
        user=current_user,
        assignments=assignments,
        all_submissions=all_submissions,
        total_assignments=len(assignments),
        total_submissions=total_submissions,
        total_graded=total_graded,
        total_pending=total_pending,
        total_flagged=total_flagged,
        avg_grade=round(avg_grade, 1),
        now=now,
    )


@app.route("/lecturer/assignments")
@lecturer_required
def lecturer_assignments():
    assignments = (
        AssignmentSubmission.query.filter_by(created_by=current_user.id)
        .order_by(AssignmentSubmission.created_at.desc())
        .all()
    )

    for assignment in assignments:
        assignment.submission_count = Submission.query.filter_by(
            assignment_id=assignment.id, is_draft=False
        ).count()
        assignment.graded_count = (
            Submission.query.filter_by(assignment_id=assignment.id, is_draft=False)
            .filter(Submission.grade.isnot(None))
            .count()
        )

    return render_template(
        "lecturer_assignments.html", assignments=assignments, now=get_current_time()
    )


@app.route("/lecturer/assignment/<int:assignment_id>/details")
@lecturer_required
def lecturer_view_assignment(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)

    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash("You don't have permission to view this assignment.", "danger")
        return redirect(url_for("lecturer_assignments"))

    submissions = Submission.query.filter_by(assignment_id=assignment_id, is_draft=False).all()
    now = get_current_time()

    return render_template(
        "lecturer_view_assignment.html",
        assignment=assignment,
        submissions=submissions,
        now=now,
    )


@app.route("/lecturer/assignment/<int:assignment_id>/edit", methods=["GET", "POST"])
@lecturer_required
def lecturer_edit_assignment(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)

    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash("You don't have permission to edit this assignment.", "danger")
        return redirect(url_for("lecturer_assignments"))

    if request.method == "POST":
        assignment.title = request.form["title"]
        assignment.course_code = request.form["course_code"].upper()
        assignment.course_title = request.form["course_title"]
        assignment.questions = request.form["questions"]
        assignment.instructions = request.form.get("instructions", "")
        assignment.deadline = datetime.strptime(
            request.form["deadline"], "%Y-%m-%dT%H:%M"
        )

        if "attachment" in request.files:
            file = request.files["attachment"]
            if file and file.filename and allowed_file(file.filename):
                if assignment.attachment_path:
                    old_path = os.path.join(
                        ASSIGNMENT_FOLDER, assignment.attachment_path
                    )
                    if os.path.exists(old_path):
                        os.remove(old_path)

                filename = secure_filename(
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
                )
                filepath = os.path.join(ASSIGNMENT_FOLDER, filename)
                file.save(filepath)
                assignment.attachment_path = filename
                assignment.attachment_filename = file.filename
                assignment.attachment_type = file.filename.rsplit(".", 1)[1].lower()

        db.session.commit()
        flash("Assignment updated successfully!", "success")
        return redirect(
            url_for("lecturer_view_assignment", assignment_id=assignment.id)
        )

    return render_template("lecturer_edit_assignment.html", assignment=assignment)


@app.route("/lecturer/assignment/<int:assignment_id>/delete", methods=["POST"])
@lecturer_required
def lecturer_delete_assignment(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)

    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash("You don't have permission to delete this assignment.", "danger")
        return redirect(url_for("lecturer_assignments"))

    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    for submission in submissions:
        if submission.file_path:
            file_path = os.path.join(SUBMISSION_FOLDER, submission.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        db.session.delete(submission)

    if assignment.attachment_path:
        file_path = os.path.join(ASSIGNMENT_FOLDER, assignment.attachment_path)
        if os.path.exists(file_path):
            os.remove(file_path)

    db.session.delete(assignment)
    db.session.commit()

    flash(f"Assignment '{assignment.title}' has been deleted.", "success")
    return redirect(url_for("lecturer_assignments"))


@app.route("/assignment/manage/<int:assignment_id>")
@lecturer_required
def manage_assignment(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)

    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash("Permission denied. You can only manage your own assignments.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    submissions = Submission.query.filter_by(assignment_id=assignment_id, is_draft=False).all()
    
    submitted_count = len(submissions)
    pending_count = len([s for s in submissions if s.grade is None])
    graded_count = len([s for s in submissions if s.grade is not None])
    plagiarism_alerts = [s for s in submissions if s.plagiarism_score > 30]
    
    graded_subs = [s for s in submissions if s.grade is not None]
    avg_grade = sum(s.grade for s in graded_subs) / len(graded_subs) if graded_subs else 0
    
    now = get_current_time()

    return render_template(
        "manage_assignment.html",
        assignment=assignment,
        submissions=submissions,
        submitted_count=submitted_count,
        pending_count=pending_count,
        graded_count=graded_count,
        avg_grade=round(avg_grade, 1),
        plagiarism_alerts=plagiarism_alerts,
        now=now,
    )


# ==================== ASSIGNMENT CREATION ROUTE ====================

@app.route("/create-assignment", methods=["GET", "POST"])
@lecturer_required
def create_assignment():
    if request.method == "POST":
        course_title = request.form["course_title"]
        course_code = request.form["course_code"].upper()
        title = request.form["title"]
        deadline_str = request.form["deadline"]
        questions = request.form["questions"]
        instructions = request.form.get("instructions", "")

        deadline = datetime.strptime(deadline_str, "%Y-%m-%dT%H:%M")

        attachment_path = None
        attachment_filename = None
        attachment_type = None

        if "attachment" in request.files:
            file = request.files["attachment"]
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
                )
                filepath = os.path.join(ASSIGNMENT_FOLDER, filename)
                file.save(filepath)
                attachment_path = filename
                attachment_filename = file.filename
                attachment_type = file.filename.rsplit(".", 1)[1].lower()

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
            created_by=current_user.id,
        )
        db.session.add(assignment)
        db.session.commit()

        activity = ActivityLog(
            user_id=current_user.id,
            action="Created assignment",
            details=f"Assignment: {title}",
        )
        db.session.add(activity)
        db.session.commit()

        flash(f"Assignment '{title}' created successfully!", "success")
        return redirect(url_for("lecturer_dashboard"))

    return render_template("create_assignment.html")


# ==================== ASSIGNMENT VIEW ROUTE (for students) ====================

@app.route("/assignment/<int:assignment_id>/view")
@login_required
def view_assignment(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    submission = None

    if current_user.is_student():
        submission = Submission.query.filter_by(
            assignment_id=assignment_id, student_id=current_user.id, is_draft=False
        ).first()

    now = get_current_time()

    return render_template(
        "view_assignment.html", assignment=assignment, submission=submission, now=now
    )


@app.route("/admin-dashboard")
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_students = User.query.filter_by(role="student").count()
    total_lecturers = User.query.filter_by(role="lecturer").count()
    total_admins = User.query.filter_by(role="admin").count()
    total_submissions = Submission.query.filter_by(is_draft=False).count()
    total_assignments = AssignmentSubmission.query.count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_activities = (
        ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(20).all()
    )

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_students=total_students,
        total_lecturers=total_lecturers,
        total_admins=total_admins,
        total_submissions=total_submissions,
        total_assignments=total_assignments,
        recent_users=recent_users,
        recent_activities=recent_activities,
    )


# ==================== SUBMISSION ROUTES ====================

@app.route("/request-verification-code/<int:assignment_id>", methods=["GET", "POST"])
@login_required
def request_verification_code(assignment_id):
    if not current_user.is_student():
        flash("Only students can submit assignments.", "danger")
        return redirect(url_for("dashboard"))

    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    
    deadline = make_naive(assignment.deadline)
    now = get_current_time()

    if deadline < now:
        flash("This assignment deadline has passed.", "danger")
        return redirect(url_for("student_dashboard"))

    existing = Submission.query.filter_by(
        assignment_id=assignment_id, student_id=current_user.id, is_draft=False
    ).first()
    if existing:
        flash("You have already submitted this assignment.", "warning")
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        verification_code = str(random.randint(100000, 999999))
        expires_at = get_current_time() + timedelta(minutes=10)

        old_codes = VerificationCode.query.filter_by(
            user_id=current_user.id, assignment_id=assignment_id, is_used=False
        ).all()
        for old in old_codes:
            db.session.delete(old)
        
        new_code = VerificationCode(
            user_id=current_user.id,
            assignment_id=assignment_id,
            code=verification_code,
            expires_at=expires_at,
            is_used=False,
        )
        db.session.add(new_code)
        db.session.commit()
        
        session.pop(f"submission_verified_{assignment_id}_{current_user.id}", None)
        session.pop(f"submission_verified_time_{assignment_id}_{current_user.id}", None)

        try:
            msg = Message(
                f"Verification Code for {assignment.title}",
                sender=app.config["MAIL_USERNAME"],
                recipients=[current_user.email],
            )
            msg.body = f"""Hello {current_user.name},

Your verification code for "{assignment.title}" is: {verification_code}

This code will expire in 10 minutes.

Enter this code on the verification page to complete your submission.

Best regards,
Submita Team
"""
            mail.send(msg)
            flash(f"Verification code sent to {current_user.email}!", "success")
        except Exception as e:
            print(f"Email error: {e}")
            flash(f"Verification code: {verification_code} (Check console if email not received)", "info")

        return redirect(url_for("verify_submission", assignment_id=assignment.id))

    return render_template("request_verification_code.html", assignment=assignment)


@app.route("/verify-submission/<int:assignment_id>", methods=["GET", "POST"])
@login_required
def verify_submission(assignment_id):
    if not current_user.is_student():
        flash("Only students can submit assignments.", "danger")
        return redirect(url_for("dashboard"))

    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    
    deadline = make_naive(assignment.deadline)
    now = get_current_time()

    if deadline < now:
        flash("This assignment deadline has passed.", "danger")
        return redirect(url_for("student_dashboard"))

    existing = Submission.query.filter_by(
        assignment_id=assignment_id, student_id=current_user.id, is_draft=False
    ).first()
    if existing:
        flash("You have already submitted this assignment.", "warning")
        return redirect(url_for("student_dashboard"))

    verification_record = (
        VerificationCode.query.filter_by(
            user_id=current_user.id, assignment_id=assignment_id, is_used=False
        )
        .order_by(VerificationCode.created_at.desc())
        .first()
    )

    if not verification_record:
        flash("No verification code found. Please request a new one.", "warning")
        return redirect(
            url_for("request_verification_code", assignment_id=assignment.id)
        )

    if request.method == "POST":
        code = request.form.get("verification_code", "").strip()

        expires_at = make_naive(verification_record.expires_at)
        if now > expires_at:
            flash("Verification code has expired. Please request a new one.", "danger")
            return redirect(
                url_for("request_verification_code", assignment_id=assignment.id)
            )

        if str(code).strip() == str(verification_record.code).strip():
            verification_record.is_used = True
            db.session.commit()
            session[f"submission_verified_{assignment_id}_{current_user.id}"] = True
            session[f"submission_verified_time_{assignment_id}_{current_user.id}"] = get_current_time().timestamp()
            flash("Code verified! You can now submit your assignment.", "success")
            return redirect(url_for("submit_assignment", assignment_id=assignment.id))
        else:
            flash("Invalid verification code. Please check and try again.", "danger")

    return render_template("verify_submission.html", assignment=assignment)


@app.route("/submit/<int:assignment_id>", methods=["GET", "POST"])
@login_required
def submit_assignment(assignment_id):
    if not current_user.is_student():
        flash("Only students can submit assignments.", "danger")
        return redirect(url_for("dashboard"))

    if not session.get(f"submission_verified_{assignment_id}_{current_user.id}"):
        flash("Please verify your email first.", "warning")
        return redirect(
            url_for("request_verification_code", assignment_id=assignment_id)
        )
    
    verification_time = session.get(f"submission_verified_time_{assignment_id}_{current_user.id}")
    if verification_time:
        current_time = get_current_time().timestamp()
        if current_time - verification_time > 600:
            session.pop(f"submission_verified_{assignment_id}_{current_user.id}", None)
            session.pop(f"submission_verified_time_{assignment_id}_{current_user.id}", None)
            flash("Verification has expired. Please request a new code.", "warning")
            return redirect(
                url_for("request_verification_code", assignment_id=assignment_id)
            )

    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    
    deadline = make_naive(assignment.deadline)
    now = get_current_time()

    if deadline < now:
        flash("This assignment deadline has passed.", "danger")
        return redirect(url_for("student_dashboard"))

    existing_submission = Submission.query.filter_by(
        assignment_id=assignment_id, student_id=current_user.id, is_draft=False
    ).first()
    
    draft = Submission.query.filter_by(
        assignment_id=assignment_id, student_id=current_user.id, is_draft=True
    ).first()

    if request.method == "POST":
        action = request.form.get("action", "submit")
        content = request.form.get("content", "").strip()
        github_url = request.form.get("github_url", "")
        file = request.files.get("file")

        filename = None
        original_filename = None
        file_type = None

        if file and file.filename and allowed_file(file.filename):
            original_filename = file.filename
            file_type = file.filename.rsplit(".", 1)[1].lower()
            filename = secure_filename(
                f"{current_user.id}_{assignment_id}_{get_current_time().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
            )
            filepath = os.path.join(SUBMISSION_FOLDER, filename)
            file.save(filepath)

        # Simple plagiarism check
        plagiarism_score = 0
        all_submissions = Submission.query.filter(
            Submission.assignment_id == assignment_id,
            Submission.is_draft == False,
            Submission.student_id != current_user.id
        ).all()
        
        for sub in all_submissions:
            if sub.content and content:
                similarity = SequenceMatcher(None, content.lower(), sub.content.lower()).ratio() * 100
                if similarity > plagiarism_score:
                    plagiarism_score = similarity

        # Save as draft
        if action == "draft":
            if draft:
                draft.content = content
                draft.file_path = filename
                draft.original_filename = original_filename
                draft.file_type = file_type
                draft.github_url = github_url
                draft.draft_saved_at = get_current_time()
            else:
                draft = Submission(
                    assignment_id=assignment_id,
                    student_id=current_user.id,
                    content=content,
                    file_path=filename,
                    original_filename=original_filename,
                    file_type=file_type,
                    github_url=github_url,
                    is_draft=True,
                    draft_saved_at=get_current_time(),
                    plagiarism_score=0
                )
                db.session.add(draft)
            
            db.session.commit()
            flash("Your draft has been saved successfully!", "success")
            return redirect(url_for("student_dashboard"))
        
        # Final submission
        if action == "submit":
            # Show warning if high plagiarism
            if plagiarism_score > 30 and not request.form.get("ignore_plagiarism"):
                return render_template(
                    "plagiarism_warning.html",
                    assignment=assignment,
                    plagiarism_score=plagiarism_score,
                    content=content,
                    filename=original_filename,
                    github_url=github_url
                )
            
            # Delete draft if exists
            if draft:
                db.session.delete(draft)
            
            # Handle resubmission
            if existing_submission:
                existing_submission.content = content
                existing_submission.file_path = filename
                existing_submission.original_filename = original_filename
                existing_submission.file_type = file_type
                existing_submission.github_url = github_url
                existing_submission.submitted_at = get_current_time()
                existing_submission.plagiarism_score = plagiarism_score
                existing_submission.resubmission_count += 1
                existing_submission.last_resubmitted_at = get_current_time()
                submission = existing_submission
            else:
                submission = Submission(
                    assignment_id=assignment_id,
                    student_id=current_user.id,
                    content=content,
                    file_path=filename,
                    original_filename=original_filename,
                    file_type=file_type,
                    github_url=github_url,
                    plagiarism_score=plagiarism_score,
                    submitted_at=get_current_time(),
                    is_draft=False,
                    resubmission_count=0
                )
                db.session.add(submission)
            
            db.session.commit()
            
            session.pop(f"submission_verified_{assignment_id}_{current_user.id}", None)
            session.pop(f"submission_verified_time_{assignment_id}_{current_user.id}", None)

            if plagiarism_score > 70:
                flash(f"⚠️ CRITICAL: Your submission has {plagiarism_score:.1f}% similarity! This may result in academic penalties.", "danger")
            elif plagiarism_score > 50:
                flash(f"⚠️ WARNING: Your submission has {plagiarism_score:.1f}% similarity. Review is recommended.", "warning")
            elif plagiarism_score > 30:
                flash(f"⚠️ Your submission has {plagiarism_score:.1f}% similarity.", "warning")
            else:
                flash(f"✅ Assignment submitted successfully! Plagiarism score: {plagiarism_score:.1f}%", "success")
            
            return redirect(url_for("student_dashboard"))

    return render_template(
        "submit.html", 
        assignment=assignment, 
        now=now,
        draft=draft,
        existing_submission=existing_submission
    )


@app.route("/plagiarism-report/<int:submission_id>")
@login_required
def plagiarism_report(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    
    if not (current_user.is_lecturer() or current_user.is_admin()):
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
    
    sub_data = {
        'id': submission.id,
        'student_name': submission.student.name,
        'student_id': submission.student.matric,
        'submitted_at': submission.submitted_at.strftime('%Y-%m-%d %H:%M'),
        'max_similarity': submission.plagiarism_score,
        'files': [submission.original_filename] if submission.file_path else [],
        'flagged': submission.plagiarism_score > 30
    }
    
    return render_template(
        "plagiarism_report.html",
        sub=sub_data,
        results=[],
        submission=submission
    )


@app.route("/grade/<int:submission_id>", methods=["GET", "POST"])
@lecturer_required
def grade_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    assignment = AssignmentSubmission.query.get(submission.assignment_id)

    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash("Permission denied. You can only grade submissions for your own assignments.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    auto_grade, breakdown = calculate_auto_grade(submission, assignment)

    if request.method == "POST":
        use_auto = request.form.get("use_auto") == "true"

        if use_auto:
            grade = auto_grade
            auto_graded = True
        else:
            grade = float(request.form["grade"])
            auto_graded = False

        feedback = request.form["feedback"]

        submission.grade = grade
        submission.feedback = feedback
        submission.auto_graded = auto_graded
        submission.grade_breakdown = json.dumps(breakdown) if breakdown else None
        db.session.commit()

        flash(f"Grade {grade}% submitted for {submission.student.name}!", "success")
        return redirect(url_for("manage_assignment", assignment_id=assignment.id))

    return render_template(
        "grade_submission.html",
        submission=submission,
        assignment=assignment,
        auto_grade=round(auto_grade, 1),
        breakdown=breakdown,
    )


# ==================== ADMIN ROUTES ====================

@app.route("/admin/users")
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=users)


@app.route("/admin/change-role/<int:user_id>", methods=["POST"])
@admin_required
def change_user_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")
    if new_role in ["student", "lecturer", "admin"]:
        user.role = new_role
        db.session.commit()
        flash(f"Role changed to {new_role.upper()}", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/delete-user/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin_users"))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "success")
    return redirect(url_for("admin_users"))


# ==================== DOWNLOAD ROUTES ====================

@app.route("/download/assignment/<int:assignment_id>")
@login_required
def download_assignment_file(assignment_id):
    assignment = AssignmentSubmission.query.get_or_404(assignment_id)
    if not assignment.attachment_path:
        flash("No file attached.", "warning")
        return redirect(request.referrer or url_for("dashboard"))
    filepath = os.path.join(ASSIGNMENT_FOLDER, assignment.attachment_path)
    if os.path.exists(filepath):
        return send_file(
            filepath, as_attachment=True, download_name=assignment.attachment_filename
        )
    flash("File not found.", "danger")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/download/submission/<int:submission_id>")
@login_required
def download_submission_file(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if not submission.file_path:
        flash("No file attached.", "warning")
        return redirect(request.referrer or url_for("dashboard"))
    filepath = os.path.join(SUBMISSION_FOLDER, submission.file_path)
    if os.path.exists(filepath):
        return send_file(
            filepath, as_attachment=True, download_name=submission.original_filename
        )
    flash("File not found.", "danger")
    return redirect(request.referrer or url_for("dashboard"))


# ==================== RUN APP ====================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(matric="ADMIN001").first():
            admin = User(
                email="admin@submita.com",
                matric="ADMIN001",
                name="System Administrator",
                password=generate_password_hash("Admin123!"),
                code="123456",
                verified=True,
                role="admin",
            )
            db.session.add(admin)
            print("✅ Admin account created: ADMIN001 / Admin123!")

        if not User.query.filter_by(matric="LEC001").first():
            lecturer = User(
                email="lecturer@mouau.edu.ng",
                matric="LEC001",
                name="Dr. John Okonkwo",
                password=generate_password_hash("Lecturer123!"),
                code="123456",
                verified=True,
                role="lecturer",
            )
            db.session.add(lecturer)
            print("✅ Lecturer account created: LEC001 / Lecturer123!")

        if not User.query.filter_by(matric="STU001").first():
            student = User(
                email="student@gmail.com",
                matric="STU001",
                name="Test Student",
                password=generate_password_hash("Student123!"),
                code="123456",
                verified=True,
                role="student",
            )
            db.session.add(student)
            print("✅ Student account created: STU001 / Student123!")

        if not User.query.filter_by(matric="STU002").first():
            student2 = User(
                email="student2@gmail.com",
                matric="STU002",
                name="Jane Doe",
                password=generate_password_hash("Student456!"),
                code="123456",
                verified=True,
                role="student",
            )
            db.session.add(student2)
            print("✅ Student account created: STU002 / Student456!")

        if not User.query.filter_by(matric="LEC002").first():
            lecturer2 = User(
                email="lecturer2@mouau.edu.ng",
                matric="LEC002",
                name="Prof. Ada Eze",
                password=generate_password_hash("Lecturer456!"),
                code="123456",
                verified=True,
                role="lecturer",
            )
            db.session.add(lecturer2)
            print("✅ Lecturer account created: LEC002 / Lecturer456!")

        db.session.commit()

        print("\n" + "=" * 50)
        print("📋 DEMO ACCOUNTS")
        print("=" * 50)
        print("Admin: ADMIN001 / Admin123!")
        print("Lecturer 1: LEC001 / Lecturer123!")
        print("Lecturer 2: LEC002 / Lecturer456!")
        print("Student 1: STU001 / Student123!")
        print("Student 2: STU002 / Student456!")
        print("=" * 50)

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)