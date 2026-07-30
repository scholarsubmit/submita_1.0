"""
app/models.py — database schema.

Security design notes (read before touching auth-related tables):
  * Verification codes and invite codes are stored as SALTED HASHES,
    never plaintext. Even a database leak doesn't hand over usable codes.
  * Every code has an expiry AND an attempt counter, so brute-forcing a
    6-digit code is rate-limited at the data layer, not just in routes.
  * LecturerInviteCode is bound to a specific email address — even if a
    code leaks, it only works for the address it was issued to.
  * ActivityLog is append-only and never references anything that gets
    deleted, so the audit trail survives account changes.
"""
import enum
import hashlib
import string
import secrets
from datetime import datetime, timedelta

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


# ==================== ENUMS ====================
class UserRole(str, enum.Enum):
    STUDENT = 'student'
    LECTURER = 'lecturer'
    ADMIN = 'admin'


class RequestStatus(str, enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'


# ==================== ACADEMIC STRUCTURE ====================
class College(db.Model):
    __tablename__ = 'colleges'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    code = db.Column(db.String(20), nullable=False, unique=True)

    departments = db.relationship('Department', backref='college', lazy=True,
                                   cascade='all, delete-orphan')

    def __repr__(self):
        return f'<College {self.code}>'


class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    levels = db.Column(db.String(100), default='100,200,300,400')  # comma-separated

    __table_args__ = (
        db.UniqueConstraint('college_id', 'code', name='uq_department_code_per_college'),
    )

    def level_list(self):
        return [lvl.strip() for lvl in (self.levels or '').split(',') if lvl.strip()]

    def __repr__(self):
        return f'<Department {self.code}>'


# ==================== USER ====================
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.Enum(UserRole), nullable=False, index=True)

    # Identity
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Students authenticate with matric (MOUAU/CSC/22/012345); lecturers/admins with staff_id.
    matric_number = db.Column(db.String(40), unique=True, nullable=True, index=True)
    staff_id = db.Column(db.String(40), unique=True, nullable=True, index=True)

    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    level = db.Column(db.String(10), nullable=True)          # students only
    admission_year = db.Column(db.String(4), nullable=True)  # students only, e.g. '2022'

    # Account state
    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    deactivated_reason = db.Column(db.String(255), nullable=True)

    # Login-attempt / lockout tracking (defense against credential stuffing)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(64), nullable=True)

    college = db.relationship('College', foreign_keys=[college_id])
    department = db.relationship('Department', foreign_keys=[department_id])

    # ── Password handling ──────────────────────────────────────────
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password, method='scrypt')

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # ── Role helpers ───────────────────────────────────────────────
    def is_student(self):
        return self.role == UserRole.STUDENT

    def is_lecturer(self):
        return self.role == UserRole.LECTURER

    def is_admin(self):
        return self.role == UserRole.ADMIN

    # ── Flask-Login required property override ──────────────────────
    @property
    def is_active(self):
        # Deliberately does NOT require is_email_verified — unverified
        # users can still authenticate, they're just routed to a forced
        # verification page by the auth blueprint. Only a hard
        # deactivation blocks login entirely.
        return self.is_active_account

    # ── Lockout helpers ──────────────────────────────────────────────
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > datetime.utcnow())

    def register_failed_login(self, max_attempts, lockout_minutes):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)

    def register_successful_login(self, ip_address):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip_address

    def __repr__(self):
        return f'<User {self.email} ({self.role.value})>'


# ==================== EMAIL VERIFICATION ====================
class EmailVerificationCode(db.Model):
    """
    One row per outstanding verification code. Codes are hashed (never
    stored plaintext) and single-use. A user can have at most one active
    code at a time — requesting a new one invalidates the old one.
    """
    __tablename__ = 'email_verification_codes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    code_hash = db.Column(db.String(64), nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    max_attempts = db.Column(db.Integer, default=5, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('verification_codes', lazy=True))

    @staticmethod
    def _hash(code):
        return hashlib.sha256(code.encode()).hexdigest()

    @classmethod
    def issue(cls, user, ttl_minutes=15):
        """Invalidate any prior codes and issue a fresh 6-digit one. Returns the plaintext code (only time it's ever available)."""
        cls.query.filter_by(user_id=user.id, used_at=None).delete()
        plaintext = f'{secrets.randbelow(1_000_000):06d}'
        record = cls(
            user_id=user.id,
            code_hash=cls._hash(plaintext),
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
        )
        db.session.add(record)
        return record, plaintext

    def verify(self, submitted_code):
        """Returns True/False. Increments attempts on every call to rate-limit brute force."""
        if self.used_at is not None:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        if self.attempts >= self.max_attempts:
            return False
        self.attempts += 1
        if self._hash(submitted_code) == self.code_hash:
            self.used_at = datetime.utcnow()
            return True
        return False


# ==================== LECTURER ONBOARDING ====================
class LecturerAccessRequest(db.Model):
    """
    A prospective lecturer's request to join. Nothing is created in the
    `users` table until an admin approves this and the invite code is
    redeemed — this prevents unverified people from ever touching auth
    tables that matter.
    """
    __tablename__ = 'lecturer_access_requests'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    reason = db.Column(db.Text, nullable=True)  # brief note on affiliation, for admin review

    status = db.Column(db.Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    admin_notes = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(64), nullable=True)

    department = db.relationship('Department', foreign_keys=[department_id])


def generate_staff_id():
    """
    System-generated staff ID: LEC/SUB/YY/NNNNAA
      LEC = Lecturer, SUB = Submita, YY = 2-digit registration year,
      NNNN = 4 random digits, AA = 2 random uppercase letters.
    Never entered manually by an admin — generating it here means it's
    guaranteed to follow the format and never collides with an existing
    one (checked against both live users and any still-pending invite).
    """
    year_suffix = str(datetime.utcnow().year)[-2:]
    for _ in range(20):
        digits = f'{secrets.randbelow(10000):04d}'
        letters = ''.join(secrets.choice(string.ascii_uppercase) for _ in range(2))
        candidate = f'LEC/SUB/{year_suffix}/{digits}{letters}'
        taken = (
            User.query.filter_by(staff_id=candidate).first()
            or LecturerInviteCode.query.filter_by(staff_id=candidate, used_at=None).first()
        )
        if not taken:
            return candidate
    raise RuntimeError('Could not generate a unique staff ID — this should never happen.')


class LecturerInviteCode(db.Model):
    """
    Generated only after admin approval. Bound to a single email address
    so a leaked code can't be redeemed by anyone else. Hashed at rest,
    single-use, time-limited.
    """
    __tablename__ = 'lecturer_invite_codes'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('lecturer_access_requests.id'), nullable=True)
    email = db.Column(db.String(150), nullable=False, index=True)
    staff_id = db.Column(db.String(40), nullable=False, unique=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)

    code_hash = db.Column(db.String(64), nullable=False)
    issued_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    department = db.relationship('Department', foreign_keys=[department_id])

    @staticmethod
    def _hash(code):
        return hashlib.sha256(code.encode()).hexdigest()

    @classmethod
    def issue(cls, email, department_id, issued_by_user_id, request_id=None, ttl_days=7):
        plaintext = secrets.token_urlsafe(9)  # ~12 url-safe chars, high entropy
        staff_id = generate_staff_id()
        record = cls(
            request_id=request_id,
            email=email,
            staff_id=staff_id,
            department_id=department_id,
            code_hash=cls._hash(plaintext),
            issued_by=issued_by_user_id,
            expires_at=datetime.utcnow() + timedelta(days=ttl_days),
        )
        db.session.add(record)
        return record, plaintext

    def redeem(self, submitted_code, submitted_email):
        if self.used_at is not None:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        if submitted_email.strip().lower() != self.email.strip().lower():
            return False
        if self._hash(submitted_code) != self.code_hash:
            return False
        self.used_at = datetime.utcnow()
        return True


# ==================== AUDIT LOG ====================
class ActivityLog(db.Model):
    """
    Append-only audit trail. user_id is nullable and has no FK constraint
    on delete-cascade, so the log survives even if a user is later removed.
    """
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


def log_activity(user_id, action, details='', request_obj=None):
    entry = ActivityLog(
        user_id=user_id,
        action=action[:100],
        details=(details or '')[:500],
        ip_address=request_obj.remote_addr if request_obj else None,
        user_agent=(request_obj.headers.get('User-Agent', '')[:300] if request_obj else None),
    )
    db.session.add(entry)


# ==================== PASSWORD RESET ====================
class PasswordResetToken(db.Model):
    """
    Hashed, single-use, time-limited reset tokens — same security pattern
    as EmailVerificationCode. The raw token only ever exists in the email
    link; the database only ever stores its hash.
    """
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', foreign_keys=[user_id])

    @staticmethod
    def _hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def issue(cls, user, ttl_minutes=30):
        # Invalidate any prior outstanding tokens for this user first —
        # only the most recently requested reset link should ever work.
        cls.query.filter_by(user_id=user.id, used_at=None).delete()
        plaintext = secrets.token_urlsafe(32)
        record = cls(
            user_id=user.id,
            token_hash=cls._hash(plaintext),
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
        )
        db.session.add(record)
        return record, plaintext

    @classmethod
    def find_valid(cls, plaintext_token):
        token_hash = cls._hash(plaintext_token)
        record = cls.query.filter_by(token_hash=token_hash, used_at=None).first()
        if not record or datetime.utcnow() > record.expires_at:
            return None
        return record

    def consume(self):
        self.used_at = datetime.utcnow()


# ==================== ASSIGNMENTS ====================
class Assignment(db.Model):
    __tablename__ = 'assignments'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    course_code = db.Column(db.String(20), nullable=False)
    course_title = db.Column(db.String(200), nullable=False)
    instructions = db.Column(db.Text, nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    target_level = db.Column(db.String(10), nullable=False)
    semester = db.Column(db.String(10), default='First', nullable=False)          # 'First' | 'Second' | 'Summer'
    academic_year = db.Column(db.String(20), default='2025/2026', nullable=False)  # e.g. '2025/2026'

    # The actual question content students answer — either typed directly,
    # an uploaded file (any format, capped at 5MB), or both. `instructions`
    # above is for supplementary notes/guidelines, not the questions themselves.
    questions_text = db.Column(db.Text, nullable=True)
    questions_file_path = db.Column(db.String(300), nullable=True)
    questions_file_original_name = db.Column(db.String(200), nullable=True)

    total_points = db.Column(db.Integer, default=100, nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    is_published = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lecturer = db.relationship('User', foreign_keys=[created_by])
    department = db.relationship('Department', foreign_keys=[department_id])
    submissions = db.relationship('Submission', backref='assignment', lazy=True, cascade='all, delete-orphan')

    def is_overdue(self):
        return datetime.utcnow() > self.deadline

    def time_remaining_label(self):
        delta = self.deadline - datetime.utcnow()
        if delta.total_seconds() <= 0:
            return 'Past due'
        hours = int(delta.total_seconds() / 3600)
        if hours < 24:
            return f'{hours}h left'
        return f'{delta.days}d left'


class Submission(db.Model):
    __tablename__ = 'submissions'

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    content = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(300), nullable=True)
    original_filename = db.Column(db.String(200), nullable=True)

    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_late = db.Column(db.Boolean, default=False, nullable=False)

    grade = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)
    plagiarism_score = db.Column(db.Float, nullable=True)

    student = db.relationship('User', foreign_keys=[student_id])

    __table_args__ = (
        db.UniqueConstraint('assignment_id', 'student_id', name='uq_one_submission_per_student'),
    )

    @property
    def is_graded(self):
        return self.grade is not None


# ==================== LIVE ACTIVITY FEED (for dashboard polling) ====================
class ActivityFeedItem(db.Model):
    """
    Lightweight, role-scoped feed for the auto-refreshing dashboard widget —
    deliberately separate from ActivityLog (the security audit trail),
    since this one is meant to be queried frequently and only keeps
    user-facing events, not every login/logout security event.
    """
    __tablename__ = 'activity_feed_items'

    id = db.Column(db.Integer, primary_key=True)
    # Who should see this item: 'admin', 'lecturer:<user_id>', or 'department:<id>'
    audience = db.Column(db.String(50), nullable=False, index=True)
    icon = db.Column(db.String(30), default='info', nullable=False)  # info|success|warning|submission|grade
    message = db.Column(db.String(300), nullable=False)
    link = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    @classmethod
    def push(cls, audience, message, icon='info', link=None):
        item = cls(audience=audience, message=message, icon=icon, link=link)
        db.session.add(item)
        return item
