"""
app/blueprints/auth.py

Covers:
  - Student self-registration (matric format enforced, email verification required)
  - Lecturer onboarding: request access -> admin approves -> invite code
    emailed -> lecturer redeems code to create their account
  - Login (matric / staff ID / email, all case-insensitive) with lockout
  - Forced email verification for students who log in before verifying
"""
from datetime import datetime, timedelta

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, session
)
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db, limiter
from app.models import (
    User, UserRole, College, Department,
    EmailVerificationCode, LecturerAccessRequest, LecturerInviteCode,
    PasswordResetToken, RequestStatus, log_activity,
)
from app.utils.security import (
    validate_matric_format, normalize_matric, validate_password_strength,
    sanitize_input, valid_email_format,
)
from app.utils.email import (
    send_verification_email, send_lecturer_invite_email, send_account_locked_email,
    send_password_reset_email,
)

auth_bp = Blueprint('auth', __name__)


# ==================== STUDENT REGISTRATION ====================
@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('8 per minute')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))

    colleges = College.query.order_by(College.name).all()

    if request.method == 'POST':
        name = sanitize_input(request.form.get('name', '')).strip()
        email = sanitize_input(request.form.get('email', '')).strip().lower()
        matric = normalize_matric(sanitize_input(request.form.get('matric', '')))
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        department_id = request.form.get('department_id', type=int)
        level = sanitize_input(request.form.get('level', ''))

        errors = []
        if len(name) < 3:
            errors.append('Please enter your full name.')
        if not valid_email_format(email):
            errors.append('Please enter a valid email address.')
        matric_ok, matric_err = validate_matric_format(matric)
        if not matric_ok:
            errors.append(matric_err)
        if password != confirm_password:
            errors.append('Passwords do not match.')
        else:
            pw_ok, pw_errors = validate_password_strength(password)
            errors.extend(pw_errors)
        if not department_id or not level:
            errors.append('Please select your department and level.')

        department = Department.query.get(department_id) if department_id else None
        if department_id and not department:
            errors.append('Invalid department selected.')

        if User.query.filter_by(email=email).first():
            errors.append('This email is already registered.')
        if User.query.filter_by(matric_number=matric).first():
            errors.append('This matric number is already registered.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return redirect(url_for('auth.register'))

        user = User(
            role=UserRole.STUDENT,
            name=name,
            email=email,
            matric_number=matric,
            college_id=department.college_id if department else None,
            department_id=department_id,
            level=level,
            admission_year='20' + matric.split('/')[2],  # from MOUAU/DEPT/YY/NNNNNN
            is_email_verified=False,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # get user.id without committing yet

        code_record, plaintext_code = EmailVerificationCode.issue(user)
        log_activity(user.id, 'account_registered', f'Student self-registration: {matric}', request)

        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            flash('Registration failed — please try again.', 'danger')
            return redirect(url_for('auth.register'))

        # Email failure must not look like registration failure — the
        # account already exists at this point.
        print(f"🔍 Registration succeeded for user id={user.id}, email={email!r} — attempting to send verification email now.")
        email_sent = send_verification_email(user, plaintext_code)
        print(f"🔍 send_verification_email returned: {email_sent}")
        if not email_sent:
            flash(
                'Account created, but we could not send your verification email. '
                'Use "Resend code" on the next page once you check your connection.',
                'warning'
            )

        session['pending_verification_user_id'] = user.id
        flash('Registration successful! Enter the 6-digit code we emailed you to activate your account.', 'success')
        return redirect(url_for('auth.verify_email'))

    return render_template('auth/register.html', colleges=colleges)


# ==================== EMAIL VERIFICATION (pre-login) ====================
@auth_bp.route('/verify-email', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def verify_email():
    user_id = session.get('pending_verification_user_id')
    user = User.query.get(user_id) if user_id else None

    if not user:
        flash('No pending verification found. Please register or log in.', 'warning')
        return redirect(url_for('auth.register'))

    if user.is_email_verified:
        session.pop('pending_verification_user_id', None)
        flash('Your email is already verified — you can log in now.', 'info')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        submitted_code = sanitize_input(request.form.get('code', '')).strip()
        record = (EmailVerificationCode.query
                  .filter_by(user_id=user.id, used_at=None)
                  .order_by(EmailVerificationCode.created_at.desc())
                  .first())

        if not record:
            flash('No active code found. Request a new one below.', 'danger')
        elif record.verify(submitted_code):
            user.is_email_verified = True
            log_activity(user.id, 'email_verified', '', request)
            db.session.commit()
            session.pop('pending_verification_user_id', None)
            flash('Email verified! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            db.session.commit()  # persist the attempt increment even on failure
            flash('Invalid or expired code. Please try again.', 'danger')

    return render_template('auth/verify_email.html', user=user)


@auth_bp.route('/verify-email/resend', methods=['POST'])
@limiter.limit('3 per 5 minutes')
def resend_verification_code():
    user_id = session.get('pending_verification_user_id')
    user = User.query.get(user_id) if user_id else None
    if not user or user.is_email_verified:
        flash('Nothing to resend.', 'warning')
        return redirect(url_for('auth.login'))

    record, plaintext_code = EmailVerificationCode.issue(user)
    db.session.commit()
    send_verification_email(user, plaintext_code)
    flash('A new code has been sent to your email.', 'success')
    return redirect(url_for('auth.verify_email'))


# ==================== LOGIN ====================
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))

    if request.method == 'POST':
        identifier = sanitize_input(request.form.get('identifier', '')).strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        id_norm = identifier.upper()
        user = User.query.filter(
            db.or_(
                User.matric_number == id_norm,
                User.staff_id == id_norm,
                User.email == identifier.lower(),
            )
        ).first()

        if not user:
            # Same generic message whether the account exists or not —
            # don't leak which identifiers are registered.
            flash('Invalid credentials.', 'danger')
            return redirect(url_for('auth.login'))

        if user.is_locked():
            minutes_left = max(1, int((user.locked_until - datetime.utcnow()).total_seconds() / 60))
            flash(f'Account temporarily locked due to repeated failed attempts. '
                  f'Try again in {minutes_left} minute(s).', 'danger')
            return redirect(url_for('auth.login'))

        if not user.is_active_account:
            flash('This account has been deactivated. Contact an administrator.', 'danger')
            return redirect(url_for('auth.login'))

        if not user.check_password(password):
            max_attempts = 5
            was_already_at_limit = user.failed_login_attempts >= max_attempts
            user.register_failed_login(max_attempts=max_attempts, lockout_minutes=15)
            db.session.commit()
            log_activity(user.id, 'login_failed', f'from {request.remote_addr}', request)
            if user.is_locked() and not was_already_at_limit:
                send_account_locked_email(user)
                flash('Too many failed attempts — account locked for 15 minutes.', 'danger')
            else:
                flash('Invalid credentials.', 'danger')
            return redirect(url_for('auth.login'))

        # Correct password — clear lockout state and log in.
        user.register_successful_login(request.remote_addr)
        log_activity(user.id, 'login_success', '', request)
        db.session.commit()
        login_user(user, remember=remember)

        if user.is_student() and not user.is_email_verified:
            flash('Please verify your email to keep full access to your account.', 'warning')
            return redirect(url_for('auth.verify_email_forced'))

        return redirect(url_for('dashboard.home'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    log_activity(current_user.id, 'logout', '', request)
    db.session.commit()
    logout_user()
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))


# ==================== FORCED VERIFICATION (post-login) ====================
@auth_bp.route('/verify-email/required', methods=['GET', 'POST'])
@login_required
@limiter.limit('10 per minute')
def verify_email_forced():
    if current_user.is_email_verified:
        return redirect(url_for('dashboard.home'))

    grace_hours = 48
    deadline = current_user.created_at + timedelta(hours=grace_hours)
    hours_remaining = max(0, int((deadline - datetime.utcnow()).total_seconds() / 3600))

    if hours_remaining <= 0:
        current_user.is_active_account = False
        current_user.deactivated_reason = 'Email not verified within grace period.'
        log_activity(current_user.id, 'account_auto_deactivated', 'Grace period expired', request)
        db.session.commit()
        logout_user()
        session.clear()
        flash('Your account was deactivated because the email verification window expired. '
              'Contact an administrator to reactivate it.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        submitted_code = sanitize_input(request.form.get('code', '')).strip()
        record = (EmailVerificationCode.query
                  .filter_by(user_id=current_user.id, used_at=None)
                  .order_by(EmailVerificationCode.created_at.desc())
                  .first())
        if record and record.verify(submitted_code):
            current_user.is_email_verified = True
            log_activity(current_user.id, 'email_verified', '', request)
            db.session.commit()
            flash('Email verified — your account is fully active.', 'success')
            return redirect(url_for('dashboard.home'))
        db.session.commit()
        flash('Invalid or expired code.', 'danger')

    return render_template('auth/verify_email_forced.html', hours_remaining=hours_remaining, grace_hours=grace_hours)


@auth_bp.route('/verify-email/required/resend', methods=['POST'])
@login_required
@limiter.limit('3 per 5 minutes')
def resend_verification_code_forced():
    if current_user.is_email_verified:
        return redirect(url_for('dashboard.home'))
    record, plaintext_code = EmailVerificationCode.issue(current_user)
    db.session.commit()
    send_verification_email(current_user, plaintext_code)
    flash('A new code has been sent to your email.', 'success')
    return redirect(url_for('auth.verify_email_forced'))


# ==================== LECTURER ONBOARDING ====================
@auth_bp.route('/lecturer/request-access', methods=['GET', 'POST'])
@limiter.limit('5 per hour')
def lecturer_request_access():
    """Step 1 of lecturer onboarding: submit a request for an admin to review.
    Creates NO user account — just a pending request."""
    departments = Department.query.order_by(Department.name).all()

    if request.method == 'POST':
        full_name = sanitize_input(request.form.get('full_name', '')).strip()
        email = sanitize_input(request.form.get('email', '')).strip().lower()
        department_id = request.form.get('department_id', type=int)
        reason = sanitize_input(request.form.get('reason', '')).strip()

        errors = []
        if len(full_name) < 3:
            errors.append('Please enter your full name.')
        if not valid_email_format(email):
            errors.append('Please enter a valid email address.')
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')
        if LecturerAccessRequest.query.filter_by(email=email, status=RequestStatus.PENDING).first():
            errors.append('You already have a pending request with this email.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return redirect(url_for('auth.lecturer_request_access'))

        req = LecturerAccessRequest(
            full_name=full_name, email=email, department_id=department_id,
            reason=reason, ip_address=request.remote_addr,
        )
        db.session.add(req)
        db.session.commit()
        flash('Your request has been submitted. An administrator will review it and, '
              'if approved, email you an invite code to complete registration.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/lecturer_request_access.html', departments=departments)


@auth_bp.route('/lecturer/onboard', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def lecturer_onboard():
    """Step 3 of lecturer onboarding: redeem an admin-issued invite code
    to actually create the account. Requires the exact email the code was
    issued to, plus the code itself — either alone is not enough."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))

    if request.method == 'POST':
        email = sanitize_input(request.form.get('email', '')).strip().lower()
        code = sanitize_input(request.form.get('code', '')).strip()
        name = sanitize_input(request.form.get('name', '')).strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        invite = (LecturerInviteCode.query
                  .filter_by(email=email, used_at=None)
                  .order_by(LecturerInviteCode.created_at.desc())
                  .first())

        if not invite or not invite.redeem(code, email):
            flash('Invalid, expired, or already-used invite code.', 'danger')
            return redirect(url_for('auth.lecturer_onboard'))

        if len(name) < 3:
            flash('Please enter your full name.', 'danger')
            return redirect(url_for('auth.lecturer_onboard'))
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.lecturer_onboard'))
        pw_ok, pw_errors = validate_password_strength(password)
        if not pw_ok:
            for e in pw_errors:
                flash(e, 'danger')
            return redirect(url_for('auth.lecturer_onboard'))

        user = User(
            role=UserRole.LECTURER,
            name=name,
            email=invite.email,
            staff_id=invite.staff_id,
            department_id=invite.department_id,
            college_id=invite.department.college_id if invite.department else None,
            # Redeeming a code emailed to this exact address IS the proof
            # of email ownership — no separate verification step needed.
            is_email_verified=True,
        )
        user.set_password(password)
        db.session.add(user)
        log_activity(None, 'lecturer_onboarded', f'staff_id={invite.staff_id}', request)
        db.session.commit()

        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/lecturer_onboard.html')


# ==================== PASSWORD RESET ====================
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('5 per hour')
def forgot_password():
    if request.method == 'POST':
        email = sanitize_input(request.form.get('email', '')).strip().lower()
        user = User.query.filter_by(email=email).first()

        # Always show the same message whether or not the account exists —
        # confirming/denying an email's existence is itself a privacy leak.
        if user and user.is_active_account:
            record, plaintext_token = PasswordResetToken.issue(user)
            db.session.commit()
            reset_link = url_for('auth.reset_password', token=plaintext_token, _external=True)
            send_password_reset_email(user, reset_link)
            log_activity(user.id, 'password_reset_requested', '', request)
            db.session.commit()

        flash('If an account exists with that email, a reset link has been sent.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@limiter.limit('10 per hour')
def reset_password(token):
    record = PasswordResetToken.find_valid(token)
    if not record:
        flash('This reset link is invalid or has expired. Request a new one.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))

        pw_ok, pw_errors = validate_password_strength(password)
        if not pw_ok:
            for e in pw_errors:
                flash(e, 'danger')
            return redirect(url_for('auth.reset_password', token=token))

        user = record.user
        user.set_password(password)
        user.failed_login_attempts = 0
        user.locked_until = None
        record.consume()
        log_activity(user.id, 'password_reset_completed', '', request)
        db.session.commit()

        flash('Password reset successfully. You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)
