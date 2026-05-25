# load_all.py - FIXED VERSION
from app import app, db
from models import College, Department, Course
import json

print("=" * 50)
print("LOADING ACADEMIC DATA")
print("=" * 50)

with app.app_context():
    # Clear existing
    print("\nClearing existing data...")
    Course.query.delete()
    Department.query.delete()
    College.query.delete()
    db.session.commit()
    print("✓ Cleared")
    
    # Load JSON
    print("\nLoading JSON file...")
    with open('academic_structure.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    colleges_data = data['Universities'][0]['colleges']
    print(f"Found {len(colleges_data)} colleges\n")
    
    college_count = 0
    dept_count = 0
    course_count = 0
    
    for college_data in colleges_data:
        college = College(
            name=college_data['name'],
            code=college_data['code'],
            description=f"{college_data['name']} - MOUAU"
        )
        db.session.add(college)
        db.session.flush()
        college_count += 1
        print(f"✓ {college.name}")
        
        for dept_data in college_data['departments']:
            department = Department(
                name=dept_data['name'],
                code=dept_data['code'],
                college_id=college.id,
                description=f"{dept_data['name']} Department"
            )
            db.session.add(department)
            db.session.flush()  # IMPORTANT: Get department.id
            dept_count += 1
            print(f"   📚 {department.name} (ID: {department.id})")
            
            # Load courses - NOW WITH CORRECT department_id
            courses_by_level = dept_data.get('courses', {})
            for level, courses in courses_by_level.items():
                for course_data in courses:
                    try:
                        course = Course(
                            code=course_data['code'],
                            title=course_data['title'],
                            credits=course_data.get('credits', 3),
                            level=level,
                            semester=course_data.get('semester', 'First'),
                            department_id=department.id,  # ← FIXED: Use department.id
                            college_id=college.id,
                            lecturer_id=1  # Default admin user
                        )
                        db.session.add(course)
                        course_count += 1
                        print(f"      📖 {course.code} - {course.title} ({level}L)")
                    except Exception as e:
                        print(f"      ⚠️ Error: {e}")
    
    db.session.commit()
    
    print("\n" + "=" * 50)
    print("✅ LOADING COMPLETE!")
    print("=" * 50)
    print(f"Colleges loaded: {college_count}")
    print(f"Departments loaded: {dept_count}")
    print(f"Courses loaded: {course_count}")
    
    # Show all colleges
    print("\n📋 COLLEGES IN DATABASE:")
    for c in College.query.order_by(College.name).all():
        depts = Department.query.filter_by(college_id=c.id).count()
        print(f"   - {c.name} ({depts} departments)")