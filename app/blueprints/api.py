"""
app/blueprints/api.py — small JSON endpoints used by form JavaScript
and dashboard polling.
"""
from flask import Blueprint, jsonify
from flask_login import login_required, current_user

from app.models import College, Department, ActivityFeedItem

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/departments/<int:college_id>')
def departments_for_college(college_id):
    departments = (Department.query
                   .filter_by(college_id=college_id)
                   .order_by(Department.name)
                   .all())
    return jsonify({
        'departments': [
            {'id': d.id, 'name': d.name, 'code': d.code, 'levels': d.levels}
            for d in departments
        ]
    })


@api_bp.route('/activity-feed')
@login_required
def activity_feed():
    """
    Returns the 20 most recent feed items visible to the current user.
    Audience scoping: admins see 'admin', lecturers see their own
    'lecturer:<id>' items, students see 'department:<dept_id>' items
    (department-wide announcements/grades relevant to them).
    """
    if current_user.is_admin():
        audiences = ['admin']
    elif current_user.is_lecturer():
        audiences = [f'lecturer:{current_user.id}']
    else:
        audiences = [f'student:{current_user.id}']
        if current_user.department_id:
            audiences.append(f'department:{current_user.department_id}')

    if not audiences:
        return jsonify({'items': []})

    items = (ActivityFeedItem.query
             .filter(ActivityFeedItem.audience.in_(audiences))
             .order_by(ActivityFeedItem.created_at.desc())
             .limit(20)
             .all())

    return jsonify({
        'items': [
            {
                'id': item.id,
                'message': item.message,
                'icon': item.icon,
                'link': item.link,
                'created_at': item.created_at.isoformat() + 'Z',
            }
            for item in items
        ]
    })
