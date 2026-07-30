"""
seed_academic_structure.py — run once (and again any time
academic_structure.json changes) to load colleges/departments into the DB.

Usage: python seed_academic_structure.py
"""
import json
import os

from app import create_app
from app.extensions import db
from app.models import College, Department

app = create_app()

with app.app_context():
    json_path = os.path.join(os.path.dirname(__file__), 'academic_structure.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    universities = data.get('Universities', [])
    if not universities:
        print('❌ No "Universities" key found in academic_structure.json')
        raise SystemExit(1)

    colleges_data = universities[0].get('colleges', [])
    college_count = 0
    dept_count = 0

    for college_data in colleges_data:
        college = College.query.filter_by(code=college_data['code']).first()
        if not college:
            college = College(name=college_data['name'], code=college_data['code'])
            db.session.add(college)
            db.session.flush()
            college_count += 1

        for dept_data in college_data.get('departments', []):
            dept = Department.query.filter_by(
                college_id=college.id, code=dept_data['code']
            ).first()
            if not dept:
                dept = Department(
                    college_id=college.id,
                    name=dept_data['name'],
                    code=dept_data['code'],
                    levels=','.join(dept_data.get('levels', ['100', '200', '300', '400'])),
                )
                db.session.add(dept)
                dept_count += 1

    db.session.commit()
    print(f'✅ Seeded {college_count} new colleges and {dept_count} new departments.')
    print(f'   Total colleges in DB: {College.query.count()}')
    print(f'   Total departments in DB: {Department.query.count()}')
