from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class UserRole:
    STUDENT = 'student'
    LECTURER = 'lecturer'
    ADMIN = 'admin'

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    matric = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(6))
    verified = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default=UserRole.STUDENT)
    department = db.Column(db.String(100), default='Computer Science')
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime)
    
    def get_id(self):
        return str(self.id)
    
    def is_admin(self):
        return self.role == UserRole.ADMIN
    
    def is_lecturer(self):
        return self.role == UserRole.LECTURER
    
    def is_student(self):
        return self.role == UserRole.STUDENT


class Assignment(db.Model):
    __tablename__ = 'assignment'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    course_code = db.Column(db.String(20))
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.now)
    plagiarism_score = db.Column(db.Float, default=0.0)
    grade = db.Column(db.Float)
    feedback = db.Column(db.Text)
    
    # Relationship - simple backref
    user = db.relationship('User', backref='assignments', foreign_keys=[user_id])


class AssignmentSubmission(db.Model):
    __tablename__ = 'assignment_submission'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    course_title = db.Column(db.String(200), nullable=False, default='')
    course_code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    questions = db.Column(db.Text, nullable=False, default='')
    instructions = db.Column(db.Text)
    attachment_path = db.Column(db.String(500))
    attachment_filename = db.Column(db.String(200))
    attachment_type = db.Column(db.String(50))
    test_cases = db.Column(db.JSON, default=list)
    deadline = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships - simple backrefs to avoid conflicts
    creator = db.relationship('User', backref='created_assignments', foreign_keys=[created_by])


class Submission(db.Model):
    __tablename__ = 'submission'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment_submission.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
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
    # NEW FIELDS
    is_draft = db.Column(db.Boolean, default=False)
    draft_saved_at = db.Column(db.DateTime)
    resubmission_count = db.Column(db.Integer, default=0)
    last_resubmitted_at = db.Column(db.DateTime)
    
    student = db.relationship('User', backref='submissions', foreign_keys=[student_id])
    assignment = db.relationship('AssignmentSubmission', backref='submissions', foreign_keys=[assignment_id])


class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    # Relationship
    user = db.relationship('User', backref='activity_logs', foreign_keys=[user_id])


class VerificationCode(db.Model):
    __tablename__ = 'verification_code'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment_submission.id'), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    
    # Relationships - simple backrefs
    user = db.relationship('User', backref='verification_codes', foreign_keys=[user_id])
    assignment = db.relationship('AssignmentSubmission', backref='verification_codes', foreign_keys=[assignment_id])