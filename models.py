# FILE: models.py
# COMPLETE VERSION with all tables for progression system - RELATIONSHIPS FIXED

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class UserRole:
    STUDENT = 'student'
    LECTURER = 'lecturer'
    ADMIN = 'admin'


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    matric = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)    
    password = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(10))
    verified = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default=UserRole.STUDENT)
    department = db.Column(db.String(100), default='Computer Science')
    college = db.Column(db.String(100), default='College of Natural Sciences')
    level = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime)
    account_active = db.Column(db.Boolean, default=True)
    
    # Student fields
    student_id = db.Column(db.String(50), unique=True, nullable=True)
    email_verified = db.Column(db.Boolean, default=False)
    email_verified_at = db.Column(db.DateTime)
    verification_token = db.Column(db.String(100), unique=True)
    token_expires_at = db.Column(db.DateTime)
    registration_number = db.Column(db.Integer)
    
    # Academic Progression Fields
    current_level = db.Column(db.String(10), default='100')
    enrollment_year = db.Column(db.String(20))
    expected_graduation_year = db.Column(db.String(20))
    program_duration = db.Column(db.Integer, default=4)
    academic_standing = db.Column(db.String(20), default='good')
    cgpa = db.Column(db.Float, default=0.0)
    total_credits_earned = db.Column(db.Integer, default=0)
    total_credits_attempted = db.Column(db.Integer, default=0)
    auto_promotion_enabled = db.Column(db.Boolean, default=True)
    
    # Foreign keys
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=True)
    
    # ========== FIXED RELATIONSHIPS - Added foreign_keys to all ==========
    submissions = db.relationship('Submission', backref='student', lazy='select', cascade='all, delete-orphan')
    created_assignments = db.relationship('Assignment', backref='creator', lazy='select', foreign_keys='Assignment.created_by')
    verification_codes = db.relationship('VerificationCode', backref='user', lazy='select')
    activity_logs = db.relationship('ActivityLog', backref='user', lazy='select')
    created_verification_codes = db.relationship('LecturerVerification', foreign_keys='LecturerVerification.created_by', backref='code_creator', lazy='select')
    
    # FIXED: Academic progress with foreign_keys
    academic_progress = db.relationship(
        'StudentAcademicProgress', 
        foreign_keys='StudentAcademicProgress.student_id',
        backref='user', 
        lazy='select', 
        cascade='all, delete-orphan'
    )
    
    # FIXED: Carry over courses with foreign_keys
    carry_over_courses = db.relationship(
        'CarryOverCourse', 
        foreign_keys='CarryOverCourse.student_id',
        backref='student', 
        lazy='select', 
        cascade='all, delete-orphan'
    )
    
    # FIXED: Promotion requests (student side)
    promotion_requests = db.relationship(
        'LevelPromotionRequest', 
        foreign_keys='LevelPromotionRequest.student_id',
        backref='student', 
        lazy='select', 
        cascade='all, delete-orphan'
    )
    
    # FIXED: Promotion requests (reviewer side)
    reviewed_promotions = db.relationship(
        'LevelPromotionRequest',
        foreign_keys='LevelPromotionRequest.reviewed_by',
        backref='reviewer',
        lazy='select'
    )
    
    __table_args__ = (
        db.Index('idx_users_email', 'email'),
        db.Index('idx_users_matric', 'matric'),
        db.Index('idx_users_role', 'role'),
        db.Index('idx_users_created_at', 'created_at'),
        db.Index('idx_users_student_id', 'student_id'),
        db.Index('idx_users_current_level', 'current_level'),
        db.Index('idx_users_department_id', 'department_id'),
        db.Index('idx_users_role_verified', 'role', 'verified'),
    )
    
    def get_id(self):
        return str(self.id)
    
    @property
    def is_active(self):
        return self.account_active and self.verified
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def is_admin(self):
        return self.role == UserRole.ADMIN
    
    def is_lecturer(self):
        return self.role == UserRole.LECTURER
    
    def is_student(self):
        return self.role == UserRole.STUDENT
    
    def __repr__(self):
        return f"<User {self.email}>"


class College(db.Model):
    __tablename__ = 'colleges'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text)
    dean_name = db.Column(db.String(200))
    dean_email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    
    departments = db.relationship('Department', backref='college_ref', lazy='select', cascade='all, delete-orphan')
    courses = db.relationship('Course', backref='college_ref', lazy='select')
    
    __table_args__ = (
        db.Index('idx_colleges_name', 'name'),
        db.Index('idx_colleges_code', 'code'),
    )
    
    def __repr__(self):
        return f"<College {self.name}>"


class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text)
    hod_name = db.Column(db.String(200))
    hod_email = db.Column(db.String(120))
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    
    courses = db.relationship('Course', backref='department_ref', lazy='select', cascade='all, delete-orphan')
    users = db.relationship('User', backref='department_ref', lazy='select')
    
    __table_args__ = (
        db.Index('idx_departments_name', 'name'),
        db.Index('idx_departments_code', 'code'),
        db.Index('idx_departments_college', 'college_id'),
    )
    
    def __repr__(self):
        return f"<Department {self.name}>"


class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    credits = db.Column(db.Integer, default=3)
    level = db.Column(db.String(10), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    academic_year = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    
    # FIXED: Added foreign_keys parameter
    enrollments = db.relationship(
        'StudentEnrollment', 
        foreign_keys='StudentEnrollment.course_id',
        backref='course_ref', 
        lazy='select', 
        cascade='all, delete-orphan'
    )
    
    # FIXED: Added foreign_keys parameter
    assignments = db.relationship(
        'Assignment', 
        foreign_keys='Assignment.course_id',  # ← THIS FIXES THE ERROR
        backref='course_ref', 
        lazy='select'
    )
    
    carry_over_students = db.relationship(
        'CarryOverCourse', 
        foreign_keys='CarryOverCourse.course_id',
        backref='course', 
        lazy='select'
    )
    
    __table_args__ = (
        db.Index('idx_courses_code', 'code'),
        db.Index('idx_courses_level', 'level'),
        db.Index('idx_courses_department', 'department_id'),
        db.Index('idx_courses_lecturer', 'lecturer_id'),
        db.UniqueConstraint('code', 'academic_year', 'semester', name='unique_course_period'),
    )
    
    def __repr__(self):
        return f"<Course {self.code} - {self.title}>"

        
class StudentEnrollment(db.Model):
    __tablename__ = 'student_enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), default='active')
    grade = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    
    student = db.relationship('User', foreign_keys=[student_id], backref='enrollments')
    course = db.relationship('Course', foreign_keys=[course_id], backref='enrolled_students', overlaps="enrollments,course_ref")
    
    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_id', 'academic_year', 'semester', name='unique_enrollment'),
        db.Index('idx_enrollments_student', 'student_id'),
        db.Index('idx_enrollments_course', 'course_id'),
        db.Index('idx_enrollments_status', 'status'),
    )


class Semester(db.Model):
    __tablename__ = 'semesters'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    semester_type = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    registration_deadline = db.Column(db.Date)
    is_current = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    __table_args__ = (
        db.Index('idx_semesters_current', 'is_current'),
        db.Index('idx_semesters_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Semester {self.name}>"


class AcademicSession(db.Model):
    __tablename__ = 'academic_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    student_progress = db.relationship('StudentAcademicProgress', backref='academic_session', lazy='select')
    promotion_requests = db.relationship('LevelPromotionRequest', backref='academic_session', lazy='select')
    
    __table_args__ = (
        db.Index('idx_academic_sessions_current', 'is_current'),
        db.Index('idx_academic_sessions_name', 'name'),
    )


class StudentAcademicProgress(db.Model):
    __tablename__ = 'student_academic_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    current_level = db.Column(db.String(10), nullable=False)
    starting_level = db.Column(db.String(10), nullable=False)
    academic_session_id = db.Column(db.Integer, db.ForeignKey('academic_sessions.id'), nullable=False)
    
    last_promotion_date = db.Column(db.DateTime)
    next_promotion_date = db.Column(db.DateTime)
    promotion_status = db.Column(db.String(20), default='active')
    
    cumulative_gpa = db.Column(db.Float, default=0.0)
    total_credits_earned = db.Column(db.Integer, default=0)
    total_credits_attempted = db.Column(db.Integer, default=0)
    
    academic_standing = db.Column(db.String(20), default='good')
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    
    # NO relationship here - defined in User class with foreign_keys
    
    __table_args__ = (
        db.Index('idx_progress_student', 'student_id'),
        db.Index('idx_progress_current_level', 'current_level'),
        db.Index('idx_progress_session', 'academic_session_id'),
        db.UniqueConstraint('student_id', 'academic_session_id', name='unique_student_session'),
    )


class CarryOverCourse(db.Model):
    __tablename__ = 'carry_over_courses'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=True)
    
    original_grade = db.Column(db.Float)
    original_semester = db.Column(db.String(20))
    original_academic_year = db.Column(db.String(20))
    
    status = db.Column(db.String(20), default='pending')
    retake_count = db.Column(db.Integer, default=1)
    
    current_semester = db.Column(db.String(20))
    current_academic_year = db.Column(db.String(20))
    
    new_grade = db.Column(db.Float)
    new_grade_date = db.Column(db.DateTime)
    
    lecturer_notes = db.Column(db.Text)
    admin_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    
    assignment = db.relationship('Assignment', foreign_keys=[assignment_id], backref='carry_over_assignments')
    # NO student relationship here - defined in User class
    
    __table_args__ = (
        db.Index('idx_carry_over_student', 'student_id'),
        db.Index('idx_carry_over_course', 'course_id'),
        db.Index('idx_carry_over_status', 'status'),
        db.UniqueConstraint('student_id', 'course_id', 'original_academic_year', name='unique_carry_over'),
    )


class LevelPromotionRequest(db.Model):
    __tablename__ = 'level_promotion_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    from_level = db.Column(db.String(10), nullable=False)
    to_level = db.Column(db.String(10), nullable=False)
    academic_session_id = db.Column(db.Integer, db.ForeignKey('academic_sessions.id'), nullable=False)
    
    request_date = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), default='pending')
    
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime)
    reviewer_notes = db.Column(db.Text)
    
    eligible_for_promotion = db.Column(db.Boolean, default=False)
    promotion_reason = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    
    # NO relationships here - defined in User class with foreign_keys
    
    __table_args__ = (
        db.Index('idx_promotion_student', 'student_id'),
        db.Index('idx_promotion_status', 'status'),
        db.Index('idx_promotion_session', 'academic_session_id'),
    )


class Assignment(db.Model):
    __tablename__ = 'assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    course_code = db.Column(db.String(20), nullable=False)
    course_title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    questions = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text)
    deadline = db.Column(db.DateTime, nullable=False)
    total_points = db.Column(db.Integer, default=100)
    attachment_path = db.Column(db.String(500))
    attachment_filename = db.Column(db.String(200))
    attachment_type = db.Column(db.String(50))
    
    # Targeting fields
    target_level = db.Column(db.String(10), nullable=False, default='100')
    target_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    target_semester = db.Column(db.String(20), nullable=False, default='First')
    target_academic_year = db.Column(db.String(20), nullable=False)
    target_course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    
    # Security fields
    is_published = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime)
    is_locked = db.Column(db.Boolean, default=False)
    late_submission_penalty = db.Column(db.Float, default=10.0)
    max_file_size = db.Column(db.Integer, default=10)
    allowed_file_types = db.Column(db.String(200))
    plagiarism_threshold = db.Column(db.Float, default=30.0)
    
    # Tracking
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    
    # Relationships
    submissions = db.relationship('Submission', backref='assignment', lazy='select', cascade='all, delete-orphan')
    target_department = db.relationship('Department', foreign_keys=[target_department_id])
    target_course = db.relationship('Course', foreign_keys=[target_course_id])
    
    __table_args__ = (
        db.Index('idx_assignments_created_by', 'created_by'),
        db.Index('idx_assignments_deadline', 'deadline'),
        db.Index('idx_assignments_is_published', 'is_published'),
        db.Index('idx_assignments_created_at', 'created_at'),
        db.Index('idx_assignments_target_level', 'target_level'),
        db.Index('idx_assignments_target_department', 'target_department_id'),
        db.Index('idx_assignments_target_semester', 'target_semester'),
        db.Index('idx_assignments_target_academic_year', 'target_academic_year'),
    )


class Submission(db.Model):
    __tablename__ = 'submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text)
    file_path = db.Column(db.String(500))
    original_filename = db.Column(db.String(200))
    file_type = db.Column(db.String(50))
    github_url = db.Column(db.String(500))
    submitted_at = db.Column(db.DateTime, default=datetime.now)
    plagiarism_score = db.Column(db.Float, default=0.0)
    grade = db.Column(db.Float)
    feedback = db.Column(db.Text)
    auto_graded = db.Column(db.Boolean, default=False)
    grade_breakdown = db.Column(db.Text)
    is_draft = db.Column(db.Boolean, default=False)
    draft_saved_at = db.Column(db.DateTime)
    resubmission_count = db.Column(db.Integer, default=0)
    last_resubmitted_at = db.Column(db.DateTime)
    
    is_late = db.Column(db.Boolean, default=False)
    late_penalty_applied = db.Column(db.Float, default=0.0)
    
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    
    __table_args__ = (
        db.Index('idx_submissions_assignment_id', 'assignment_id'),
        db.Index('idx_submissions_student_id', 'student_id'),
        db.Index('idx_submissions_submitted_at', 'submitted_at'),
        db.Index('idx_submissions_grade', 'grade'),
        db.Index('idx_submissions_is_draft', 'is_draft'),
        db.Index('idx_submissions_assignment_student', 'assignment_id', 'student_id'),
        db.Index('idx_submissions_plagiarism_score', 'plagiarism_score'),
    )


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    __table_args__ = (
        db.Index('idx_activity_logs_user_id', 'user_id'),
        db.Index('idx_activity_logs_timestamp', 'timestamp'),
        db.Index('idx_activity_logs_action', 'action'),
    )


class VerificationCode(db.Model):
    __tablename__ = 'verification_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=True)
    code = db.Column(db.String(10), nullable=False)
    purpose = db.Column(db.String(50), default='email_verification')
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    __table_args__ = (
        db.Index('idx_verification_codes_user', 'user_id'),
        db.Index('idx_verification_codes_code', 'code'),
        db.Index('idx_verification_codes_expires', 'expires_at'),
    )


class LecturerVerification(db.Model):
    __tablename__ = 'lecturer_verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    verification_code = db.Column(db.String(50), unique=True, nullable=False)
    verification_code_hash = db.Column(db.String(255), nullable=True)
    staff_id = db.Column(db.String(50), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(200))
    college = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    used_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    used_at = db.Column(db.DateTime)
    
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    email_opens = db.Column(db.Integer, default=0)
    last_opened_at = db.Column(db.DateTime)
    
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    security_token = db.Column(db.String(100), unique=True)
    
    verification_attempts = db.Column(db.Integer, default=0)
    last_verification_attempt = db.Column(db.DateTime)
    
    __table_args__ = (
        db.Index('idx_lecturer_verification_code', 'verification_code'),
        db.Index('idx_lecturer_verification_email', 'email'),
        db.Index('idx_lecturer_verification_expires', 'expires_at'),
        db.Index('idx_lecturer_verification_used', 'is_used'),
    )
    
    def __repr__(self):
        return f"<LecturerVerification {self.verification_code[:15]}... for {self.email}>"


class LecturerRegistrationRequest(db.Model):
    __tablename__ = 'lecturer_registration_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    staff_id = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(200), nullable=False)
    college = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    qualification = db.Column(db.String(200))
    years_of_experience = db.Column(db.Integer, default=0)
    specializations = db.Column(db.Text)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    admin_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    requester = db.relationship('User', foreign_keys=[user_id], backref='lecturer_requests')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_requests')
    
    __table_args__ = (
        db.Index('idx_lecturer_requests_status', 'status'),
        db.Index('idx_lecturer_requests_email', 'email'),
        db.Index('idx_lecturer_requests_created', 'created_at'),
    )


def get_current_semester():
    return Semester.query.filter_by(is_current=True, is_active=True).first()


def is_student_enrolled(student_id, course_id, academic_year, semester):
    enrollment = StudentEnrollment.query.filter_by(
        student_id=student_id,
        course_id=course_id,
        academic_year=academic_year,
        semester=semester,
        status='active'
    ).first()
    return enrollment is not None