from datetime import datetime
from enum import Enum

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class UserRole:
    STUDENT = "student"
    LECTURER = "lecturer"
    ADMIN = "admin"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    matric = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(6))
    verified = db.Column(db.Boolean, default=False)
    role = db.Column(
        db.String(20), default=UserRole.STUDENT
    )  # student, lecturer, admin
    department = db.Column(db.String(100), default="Computer Science")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    assignments = db.relationship("Assignment", backref="author", lazy=True)
    submissions = db.relationship("Submission", backref="student", lazy=True)
    created_assignments = db.relationship(
        "AssignmentSubmission", backref="creator", lazy=True
    )
    activities = db.relationship("ActivityLog", backref="user", lazy=True)

    def get_id(self):
        return str(self.id)

    def is_admin(self):
        return self.role == UserRole.ADMIN

    def is_lecturer(self):
        return self.role == UserRole.LECTURER

    def is_student(self):
        return self.role == UserRole.STUDENT


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    course_code = db.Column(db.String(20))
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    plagiarism_score = db.Column(db.Float, default=0.0)
    grade = db.Column(db.Float)
    feedback = db.Column(db.Text)


class AssignmentSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    course_title = db.Column(db.String(200), nullable=False)  # New: Course Title
    course_code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)  # Rich text description
    questions = db.Column(db.Text)  # Typed questions (max 10k chars)
    instructions = db.Column(db.Text)  # Optional instructions
    attachment_path = db.Column(db.String(500))  # File attachment path
    attachment_filename = db.Column(db.String(200))  # Original filename
    attachment_type = db.Column(db.String(50))  # File type
    deadline = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submissions = db.relationship("Submission", backref="assignment", lazy=True)


class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("assignment_submission.id"), nullable=False
    )
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text)  # Text answer if any
    file_path = db.Column(db.String(500))  # Student's uploaded file
    original_filename = db.Column(db.String(200))  # Student's original filename
    file_type = db.Column(db.String(50))  # File type
    github_url = db.Column(db.String(500))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    plagiarism_score = db.Column(db.Float, default=0.0)
    grade = db.Column(db.Float)
    feedback = db.Column(db.Text)


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
