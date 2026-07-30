"""
app/blueprints/results.py — cross-assignment result compilation.
"""
import csv
import io
from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file
from flask_login import login_required, current_user

from app.models import Department
from app.utils.results import compile_course_results, distinct_result_groups

results_bp = Blueprint('results', __name__)


def lecturer_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if not (current_user.is_lecturer() or current_user.is_admin()):
            flash('Lecturer access required.', 'danger')
            return redirect(url_for('dashboard.home'))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin():
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard.home'))
        return view(*args, **kwargs)
    return wrapper


def _build_csv(assignments, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    header = ['Matric Number', 'Student Name'] + [a.title for a in assignments] + ['Total', 'Average']
    writer.writerow(header)
    for row in rows:
        line = [row['student'].matric_number, row['student'].name]
        for a in assignments:
            score = row['scores'].get(a.id)
            line.append(score if score is not None else '')
        line.append(row['total'])
        line.append(row['average'] if row['average'] is not None else '')
        writer.writerow(line)
    return buffer.getvalue()


# ==================== LECTURER ====================
@results_bp.route('/lecturer/results')
@lecturer_required
def lecturer_results():
    groups = distinct_result_groups(lecturer_id=current_user.id)
    return render_template('lecturer/results_list.html', groups=groups)


@results_bp.route('/lecturer/results/sheet')
@lecturer_required
def lecturer_result_sheet():
    course_code = request.args.get('course_code', '')
    target_level = request.args.get('target_level', '')
    semester = request.args.get('semester', '')
    academic_year = request.args.get('academic_year', '')

    compiled = compile_course_results(
        department_id=current_user.department_id, target_level=target_level,
        semester=semester, academic_year=academic_year,
        course_code=course_code, lecturer_id=current_user.id,
    )
    return render_template(
        'lecturer/result_sheet.html', compiled=compiled, course_code=course_code,
        target_level=target_level, semester=semester, academic_year=academic_year,
    )


@results_bp.route('/lecturer/results/sheet/export')
@lecturer_required
def lecturer_result_sheet_export():
    course_code = request.args.get('course_code', '')
    target_level = request.args.get('target_level', '')
    semester = request.args.get('semester', '')
    academic_year = request.args.get('academic_year', '')

    compiled = compile_course_results(
        department_id=current_user.department_id, target_level=target_level,
        semester=semester, academic_year=academic_year,
        course_code=course_code, lecturer_id=current_user.id,
    )
    csv_data = _build_csv(compiled['assignments'], compiled['rows'])
    mem = io.BytesIO(csv_data.encode('utf-8'))
    filename = f'{course_code}_{target_level}L_{semester}_{academic_year.replace("/", "-")}_results.csv'
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=filename)


# ==================== ADMIN ====================
@results_bp.route('/admin/results')
@admin_required
def admin_results():
    groups = distinct_result_groups()  # every department/lecturer, not scoped
    return render_template('admin/results_list.html', groups=groups)


@results_bp.route('/admin/results/sheet')
@admin_required
def admin_result_sheet():
    department_id = request.args.get('department_id', type=int)
    course_code = request.args.get('course_code', '')
    target_level = request.args.get('target_level', '')
    semester = request.args.get('semester', '')
    academic_year = request.args.get('academic_year', '')

    compiled = compile_course_results(
        department_id=department_id, target_level=target_level,
        semester=semester, academic_year=academic_year, course_code=course_code,
    )
    department = Department.query.get(department_id)
    return render_template(
        'admin/result_sheet.html', compiled=compiled, course_code=course_code,
        department=department, target_level=target_level, semester=semester, academic_year=academic_year,
    )


@results_bp.route('/admin/results/sheet/export')
@admin_required
def admin_result_sheet_export():
    department_id = request.args.get('department_id', type=int)
    course_code = request.args.get('course_code', '')
    target_level = request.args.get('target_level', '')
    semester = request.args.get('semester', '')
    academic_year = request.args.get('academic_year', '')

    compiled = compile_course_results(
        department_id=department_id, target_level=target_level,
        semester=semester, academic_year=academic_year, course_code=course_code,
    )
    csv_data = _build_csv(compiled['assignments'], compiled['rows'])
    mem = io.BytesIO(csv_data.encode('utf-8'))
    filename = f'{course_code}_{target_level}L_{semester}_{academic_year.replace("/", "-")}_results.csv'
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=filename)
