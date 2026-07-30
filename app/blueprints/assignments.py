"""
app/blueprints/assignments.py

Phase 3 additions on top of Phase 2's create/publish/submit/grade:
  - File upload for submissions (alongside or instead of text content)
  - Automatic plagiarism check against other submissions for the SAME
    assignment, recomputed for everyone whenever a new submission lands
    (a new submission can raise an existing one's similarity score too)
  - AI grading suggestion (Claude API) — a lecturer explicitly requests
    it, reviews it, and only THEN it becomes the real grade on submit.
    Never auto-applied.
  - CSV result export per assignment ("auto result compilation")
"""
import csv
import io
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, send_file, send_from_directory, abort, current_app
)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Assignment, Submission, ActivityFeedItem, log_activity
from app.utils.security import sanitize_input
from app.utils.uploads import save_submission_file, save_question_file
from app.utils.plagiarism import check_submission_against_peers, severity_for_score
from app.utils.ai_grading import get_ai_grade_suggestion
from app.utils.results import compile_course_results

assignments_bp = Blueprint('assignments', __name__)


def lecturer_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if not (current_user.is_lecturer() or current_user.is_admin()):
            flash('Lecturer access required.', 'danger')
            return redirect(url_for('dashboard.home'))
        return view(*args, **kwargs)
    return wrapper


def _recompute_plagiarism_for_assignment(assignment_id):
    """Recomputes plagiarism_score for every submission on this assignment.
    A new submission can raise the similarity score of an EXISTING one
    too, so this recomputes the whole set rather than just the newcomer."""
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    for sub in submissions:
        highest, _ = check_submission_against_peers(sub, submissions)
        sub.plagiarism_score = highest


# ==================== LECTURER SIDE ====================
@assignments_bp.route('/lecturer/assignments/new', methods=['GET', 'POST'])
@lecturer_required
def create_assignment():
    if request.method == 'POST':
        title = sanitize_input(request.form.get('title', '')).strip()
        course_code = sanitize_input(request.form.get('course_code', '')).strip().upper()
        course_title = sanitize_input(request.form.get('course_title', '')).strip()
        instructions = sanitize_input(request.form.get('instructions', ''))
        questions_text = sanitize_input(request.form.get('questions_text', ''))
        questions_file = request.files.get('questions_file')
        target_level = sanitize_input(request.form.get('target_level', ''))
        semester = sanitize_input(request.form.get('semester', 'First'))
        academic_year = sanitize_input(request.form.get('academic_year', '')).strip()
        deadline_str = request.form.get('deadline', '')
        total_points = request.form.get('total_points', type=int) or 100
        action = request.form.get('action', 'publish')

        errors = []
        if not title:
            errors.append('Title is required.')
        if not course_code or not course_title:
            errors.append('Course code and title are required.')
        if not target_level:
            errors.append('Please select a target level.')
        if not academic_year:
            errors.append('Please select an academic year.')
        if not questions_text.strip() and not (questions_file and questions_file.filename):
            errors.append('Provide the questions either by typing them or uploading a file.')
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            errors.append('Please choose a valid deadline.')
            deadline = None
        if not current_user.department_id:
            errors.append('Your account has no department set — contact an admin.')

        questions_file_name, questions_file_original, file_error = (None, None, None)
        if questions_file and questions_file.filename:
            questions_file_name, questions_file_original, file_error = save_question_file(questions_file)
            if file_error:
                errors.append(file_error)

        if errors:
            for e in errors:
                flash(e, 'danger')
            return redirect(url_for('assignments.create_assignment'))

        assignment = Assignment(
            title=title, course_code=course_code, course_title=course_title,
            instructions=instructions,
            questions_text=questions_text or None,
            questions_file_path=questions_file_name,
            questions_file_original_name=questions_file_original,
            created_by=current_user.id,
            department_id=current_user.department_id, target_level=target_level,
            semester=semester, academic_year=academic_year,
            total_points=total_points, deadline=deadline,
            is_published=(action == 'publish'),
        )
        db.session.add(assignment)
        db.session.flush()

        if assignment.is_published:
            ActivityFeedItem.push(
                audience=f'department:{current_user.department_id}',
                message=f'New assignment posted: "{title}" ({course_code}) — due {deadline.strftime("%b %d")}',
                icon='info', link=url_for('assignments.view_assignment', assignment_id=assignment.id),
            )
        log_activity(current_user.id, 'assignment_created', title, request)
        db.session.commit()

        flash('Assignment published!' if assignment.is_published else 'Saved as draft.', 'success')
        return redirect(url_for('dashboard.home'))

    return render_template('lecturer/create_assignment.html')


@assignments_bp.route('/lecturer/assignments/<int:assignment_id>')
@lecturer_required
def manage_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash('You can only manage your own assignments.', 'danger')
        return redirect(url_for('dashboard.home'))

    submissions = (Submission.query
                   .filter_by(assignment_id=assignment.id)
                   .order_by(Submission.submitted_at.desc())
                   .all())
    graded = [s for s in submissions if s.is_graded]
    avg_grade = round(sum(s.grade for s in graded) / len(graded), 1) if graded else None

    return render_template(
        'lecturer/manage_assignment.html', assignment=assignment,
        submissions=submissions, avg_grade=avg_grade,
        severity_for_score=severity_for_score,
    )


@assignments_bp.route('/lecturer/assignments/<int:assignment_id>/export-results')
@lecturer_required
def export_results(assignment_id):
    """Per-assignment CSV export (was already here). For a compiled
    result sheet across an ENTIRE course, see /lecturer/results below."""
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard.home'))

    submissions = (Submission.query
                   .filter_by(assignment_id=assignment.id)
                   .order_by(Submission.grade.desc().nullslast())
                   .all())

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Matric Number', 'Student Name', 'Submitted At', 'Late', 'Grade', 'Out Of', 'Plagiarism %', 'Feedback'])
    for s in submissions:
        writer.writerow([
            s.student.matric_number, s.student.name,
            s.submitted_at.strftime('%Y-%m-%d %H:%M'), 'Yes' if s.is_late else 'No',
            s.grade if s.grade is not None else '', assignment.total_points,
            s.plagiarism_score if s.plagiarism_score is not None else '',
            (s.feedback or '').replace('\n', ' '),
        ])

    log_activity(current_user.id, 'results_exported', assignment.title, request)
    db.session.commit()

    mem = io.BytesIO(buffer.getvalue().encode('utf-8'))
    filename = f'{assignment.course_code}_{assignment.title.replace(" ", "_")}_results.csv'
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=filename)


# ==================== CROSS-ASSIGNMENT RESULT COMPILATION ====================
@assignments_bp.route('/lecturer/results')
@lecturer_required
def my_courses():
    """Lists each distinct course this lecturer teaches (by course_code),
    with a count of assignments, as the entry point into compiled results."""
    my_assignments = Assignment.query.filter_by(created_by=current_user.id).all()
    courses = {}
    for a in my_assignments:
        key = a.course_code
        if key not in courses:
            courses[key] = {'course_code': a.course_code, 'course_title': a.course_title, 'assignment_count': 0}
        courses[key]['assignment_count'] += 1
    return render_template('lecturer/my_courses.html', courses=sorted(courses.values(), key=lambda c: c['course_code']))


@assignments_bp.route('/lecturer/results/<course_code>')
@lecturer_required
def course_results(course_code):
    assignments = Assignment.query.filter_by(created_by=current_user.id, course_code=course_code).all()
    if not assignments:
        flash('No assignments found for that course.', 'warning')
        return redirect(url_for('assignments.my_courses'))

    compiled = compile_course_results(assignments)
    return render_template('lecturer/course_results.html', course_code=course_code,
                            course_title=assignments[0].course_title, compiled=compiled)


@assignments_bp.route('/lecturer/results/<course_code>/export')
@lecturer_required
def export_course_results(course_code):
    assignments = Assignment.query.filter_by(created_by=current_user.id, course_code=course_code).all()
    if not assignments:
        flash('No assignments found for that course.', 'warning')
        return redirect(url_for('assignments.my_courses'))

    compiled = compile_course_results(assignments)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    header = ['Matric Number', 'Student Name'] + [a.title for a in compiled['assignments']] + ['Total', 'Out Of', 'Percentage']
    writer.writerow(header)
    for row in compiled['rows']:
        cells = []
        for a in compiled['assignments']:
            cell = row['cells'][a.id]
            cells.append(cell['grade'] if cell['status'] == 'graded' else cell['status'].upper())
        writer.writerow(
            [row['student'].matric_number, row['student'].name] + cells +
            [row['total_earned'] if row['total_earned'] is not None else 'INCOMPLETE',
             compiled['total_possible'],
             f"{row['percentage']}%" if row['percentage'] is not None else 'INCOMPLETE']
        )

    log_activity(current_user.id, 'course_results_exported', course_code, request)
    db.session.commit()

    mem = io.BytesIO(buffer.getvalue().encode('utf-8'))
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=f'{course_code}_compiled_results.csv')


@assignments_bp.route('/lecturer/submissions/<int:submission_id>/plagiarism-report')
@lecturer_required
def plagiarism_report(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    assignment = submission.assignment
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard.home'))

    all_submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
    _, matches = check_submission_against_peers(submission, all_submissions)
    label, color = severity_for_score(submission.plagiarism_score or 0)

    return render_template(
        'lecturer/plagiarism_report.html', submission=submission, assignment=assignment,
        matches=matches, severity_label=label, severity_color=color,
    )


@assignments_bp.route('/lecturer/submissions/<int:submission_id>/grade', methods=['GET', 'POST'])
@lecturer_required
def grade_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    assignment = submission.assignment
    if assignment.created_by != current_user.id and not current_user.is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard.home'))

    ai_suggestion = None

    if request.method == 'POST':
        action = request.form.get('form_action', 'save')

        if action == 'ai_suggest':
            ai_suggestion = get_ai_grade_suggestion(assignment, submission.content)
            if ai_suggestion is None:
                flash('AI grading is unavailable right now — grade manually below, '
                      'or check that ANTHROPIC_API_KEY is configured.', 'warning')
            return render_template(
                'lecturer/grade_submission.html', submission=submission,
                assignment=assignment, ai_suggestion=ai_suggestion,
            )

        grade = request.form.get('grade', type=float)
        feedback = sanitize_input(request.form.get('feedback', ''))
        if grade is None or grade < 0 or grade > assignment.total_points:
            flash(f'Grade must be between 0 and {assignment.total_points}.', 'danger')
            return redirect(url_for('assignments.grade_submission', submission_id=submission_id))

        submission.grade = grade
        submission.feedback = feedback
        submission.graded_at = datetime.utcnow()

        ActivityFeedItem.push(
            audience=f'student:{submission.student_id}',
            message=f'Your submission for "{assignment.title}" was graded: {grade}/{assignment.total_points}',
            icon='grade', link=url_for('assignments.view_assignment', assignment_id=assignment.id),
        )
        log_activity(current_user.id, 'submission_graded', f'submission_id={submission.id}', request)
        db.session.commit()

        flash('Grade saved.', 'success')
        return redirect(url_for('assignments.manage_assignment', assignment_id=assignment.id))

    return render_template('lecturer/grade_submission.html', submission=submission,
                            assignment=assignment, ai_suggestion=None)


# ==================== STUDENT SIDE ====================
@assignments_bp.route('/assignments/<int:assignment_id>')
@login_required
def view_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    existing_submission = None
    if current_user.is_student():
        existing_submission = Submission.query.filter_by(
            assignment_id=assignment.id, student_id=current_user.id
        ).first()
    return render_template('student/view_assignment.html', assignment=assignment, submission=existing_submission)


@assignments_bp.route('/assignments/<int:assignment_id>/question-file')
@login_required
def download_question_file(assignment_id):
    """
    Serves the lecturer-uploaded question paper. Not under /static/, so
    access is gated: the assignment's own lecturer, any admin, or a
    student whose department + level actually matches the assignment's
    target (same rule used to decide whether it shows on their dashboard).
    """
    assignment = Assignment.query.get_or_404(assignment_id)
    if not assignment.questions_file_path:
        abort(404)

    is_owner_or_admin = current_user.is_admin() or assignment.created_by == current_user.id
    is_targeted_student = (
        current_user.is_student()
        and current_user.department_id == assignment.department_id
        and current_user.level == assignment.target_level
    )
    if not (is_owner_or_admin or is_targeted_student):
        abort(403)
    if is_targeted_student and not assignment.is_published:
        abort(404)  # don't let students fetch files for unpublished drafts

    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'], assignment.questions_file_path,
        as_attachment=True, download_name=assignment.questions_file_original_name,
    )


@assignments_bp.route('/assignments/<int:assignment_id>/submit', methods=['GET', 'POST'])
@login_required
def submit_assignment(assignment_id):
    if not current_user.is_student():
        flash('Only students can submit assignments.', 'danger')
        return redirect(url_for('dashboard.home'))

    assignment = Assignment.query.get_or_404(assignment_id)
    if not assignment.is_published:
        flash('This assignment is not yet available.', 'warning')
        return redirect(url_for('dashboard.home'))

    existing = Submission.query.filter_by(assignment_id=assignment.id, student_id=current_user.id).first()
    if existing:
        flash('You have already submitted this assignment.', 'warning')
        return redirect(url_for('assignments.view_assignment', assignment_id=assignment.id))

    if request.method == 'POST':
        content = sanitize_input(request.form.get('content', ''))
        uploaded_file = request.files.get('file')

        stored_name, original_name, upload_error = save_submission_file(uploaded_file)
        if upload_error:
            flash(upload_error, 'danger')
            return redirect(url_for('assignments.submit_assignment', assignment_id=assignment_id))

        if not content.strip() and not stored_name:
            flash('Please write your answer or attach a file.', 'danger')
            return redirect(url_for('assignments.submit_assignment', assignment_id=assignment_id))

        submission = Submission(
            assignment_id=assignment.id, student_id=current_user.id, content=content,
            file_path=stored_name, original_filename=original_name,
            is_late=assignment.is_overdue(),
        )
        db.session.add(submission)
        db.session.flush()

        # Plagiarism check runs automatically the moment the submission lands.
        _recompute_plagiarism_for_assignment(assignment.id)

        ActivityFeedItem.push(
            audience=f'lecturer:{assignment.created_by}',
            message=f'{current_user.name} submitted "{assignment.title}"' + (' (late)' if submission.is_late else ''),
            icon='submission', link=url_for('assignments.manage_assignment', assignment_id=assignment.id),
        )
        log_activity(current_user.id, 'assignment_submitted', assignment.title, request)
        db.session.commit()

        flash('Submitted successfully!', 'success')
        return redirect(url_for('dashboard.home'))

    return render_template('student/submit_assignment.html', assignment=assignment)
