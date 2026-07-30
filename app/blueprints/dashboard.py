"""
app/blueprints/dashboard.py — role-specific dashboards with live data.
"""
from datetime import datetime

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.models import Assignment, Submission, User, UserRole, LecturerAccessRequest, RequestStatus

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def home():
    if current_user.is_admin():
        return _admin_dashboard()
    if current_user.is_lecturer():
        return _lecturer_dashboard()
    return _student_dashboard()


def _student_dashboard():
    submitted_ids = [
        s[0] for s in
        Submission.query.with_entities(Submission.assignment_id)
        .filter_by(student_id=current_user.id).all()
    ]

    query = (Assignment.query
             .filter_by(department_id=current_user.department_id, target_level=current_user.level, is_published=True)
             .filter(Assignment.deadline > datetime.utcnow()))
    if submitted_ids:
        query = query.filter(~Assignment.id.in_(submitted_ids))
    upcoming = query.order_by(Assignment.deadline.asc()).all()

    my_submissions = (Submission.query
                       .filter_by(student_id=current_user.id)
                       .order_by(Submission.submitted_at.desc())
                       .limit(5).all())

    graded = [s for s in Submission.query.filter_by(student_id=current_user.id).all() if s.is_graded]
    avg_grade = round(sum(s.grade for s in graded) / len(graded), 1) if graded else None

    # Attach an urgency label for the deadline-first UI
    for a in upcoming:
        hours_left = (a.deadline - datetime.utcnow()).total_seconds() / 3600
        a.urgency = 'critical' if hours_left <= 24 else ('soon' if hours_left <= 72 else 'normal')

    return render_template(
        'student/dashboard.html',
        upcoming=upcoming, my_submissions=my_submissions,
        total_submissions=Submission.query.filter_by(student_id=current_user.id).count(),
        avg_grade=avg_grade,
    )


def _lecturer_dashboard():
    my_assignments = (Assignment.query
                       .filter_by(created_by=current_user.id)
                       .order_by(Assignment.created_at.desc())
                       .all())

    total_submissions = 0
    pending_grading = 0
    for a in my_assignments:
        subs = Submission.query.filter_by(assignment_id=a.id).all()
        a.submission_count = len(subs)
        a.pending_count = len([s for s in subs if not s.is_graded])
        total_submissions += len(subs)
        pending_grading += a.pending_count

    recent_submissions = (Submission.query
                           .join(Assignment)
                           .filter(Assignment.created_by == current_user.id)
                           .order_by(Submission.submitted_at.desc())
                           .limit(8).all())

    return render_template(
        'lecturer/dashboard.html',
        assignments=my_assignments, total_assignments=len(my_assignments),
        total_submissions=total_submissions, pending_grading=pending_grading,
        recent_submissions=recent_submissions,
    )


def _admin_dashboard():
    stats = {
        'total_students': User.query.filter_by(role=UserRole.STUDENT).count(),
        'total_lecturers': User.query.filter_by(role=UserRole.LECTURER).count(),
        'total_assignments': Assignment.query.count(),
        'total_submissions': Submission.query.count(),
        'pending_lecturer_requests': LecturerAccessRequest.query.filter_by(status=RequestStatus.PENDING).count(),
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(8).all()
    return render_template('admin/dashboard.html', stats=stats, recent_users=recent_users)
