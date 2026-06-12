# load_all.py - FIXED for your JSON structure
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
    
    # Navigate the JSON structure
    # Your JSON has: Universities -> [0] -> colleges -> []
    universities = data.get('Universities', [])
    if not universities:
        print("❌ No 'Universities' key found in JSON")
        exit(1)
    
    university = universities[0]
    colleges_data = university.get('colleges', [])
    
    print(f"Found {len(colleges_data)} colleges in JSON\n")
    
    college_count = 0
    dept_count = 0
    course_count = 0
    
    for college_data in colleges_data:
        college_name = college_data.get('name')
        college_code = college_data.get('code')
        
        if not college_name:
            print(f"⚠️ Skipping college without name: {college_data}")
            continue
        
        # Create college
        college = College(
            name=college_name,
            code=college_code,
            description=f"{college_name} - {university.get('name', 'MOUAU')}"
        )
        db.session.add(college)
        db.session.flush()
        college_count += 1
        print(f"\n✓ College {college_count}: {college.name} ({college.code})")
        
        # Add departments
        departments_list = college_data.get('departments', [])
        print(f"   📚 Adding {len(departments_list)} departments...")
        
        for dept_data in departments_list:
            dept_name = dept_data.get('name')
            dept_code = dept_data.get('code')
            
            if not dept_name:
                continue
            
            department = Department(
                name=dept_name,
                code=dept_code,
                college_id=college.id,
                description=f"{dept_name} Department"
            )
            db.session.add(department)
            db.session.flush()
            dept_count += 1
            print(f"      📚 {dept_name} ({dept_code})")
            
            # Load courses if any
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
                            department_id=department.id,
                            college_id=college.id,
                            lecturer_id=1
                        )
                        db.session.add(course)
                        course_count += 1
                        print(f"         📖 {course.code} - {course.title} ({level}L)")
                    except Exception as e:
                        print(f"         ⚠️ Error adding course: {e}")
    
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