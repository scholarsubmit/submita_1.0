#!/usr/bin/env python3
"""
Complete Mock Data Seeder for Submita Platform
Populates all tables with realistic test data
"""

import os
import sys
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import (
    User, UserRole, College, Department, Course, Assignment, Submission,
    StudentEnrollment, Semester, AcademicSession, StudentAcademicProgress,
    CarryOverCourse, LevelPromotionRequest, VerificationCode,
    LecturerVerification, LecturerRegistrationRequest, ActivityLog
)

# Configuration
PASSWORD_HASH = generate_password_hash('password123')

# Nigerian Universities Data
UNIVERSITIES = [
    {'name': 'University of Lagos', 'code': 'UNILAG', 'dean': 'Prof. Adeola Johnson', 'dean_email': 'dean@unilag.edu.ng'},
    {'name': 'University of Ibadan', 'code': 'UI', 'dean': 'Prof. Olufemi Adeyemi', 'dean_email': 'dean@ui.edu.ng'},
    {'name': 'Obafemi Awolowo University', 'code': 'OAU', 'dean': 'Prof. Temitope Ogunlesi', 'dean_email': 'dean@oau.edu.ng'},
]

DEPARTMENTS_DATA = {
    'Faculty of Science': [
        {'name': 'Computer Science', 'code': 'CSC', 'hod': 'Prof. Adewale Johnson', 'hod_email': 'hod.csc@university.edu'},
        {'name': 'Mathematics', 'code': 'MTH', 'hod': 'Prof. Olu Adebayo', 'hod_email': 'hod.mth@university.edu'},
        {'name': 'Physics', 'code': 'PHY', 'hod': 'Dr. Emeka Okafor', 'hod_email': 'hod.phy@university.edu'},
    ],
    'Faculty of Engineering': [
        {'name': 'Electrical Engineering', 'code': 'EEE', 'hod': 'Prof. Tunde Balogun', 'hod_email': 'hod.eee@university.edu'},
        {'name': 'Mechanical Engineering', 'code': 'MEE', 'hod': 'Dr. Chinedu Nwachukwu', 'hod_email': 'hod.mee@university.edu'},
    ],
    'Faculty of Social Sciences': [
        {'name': 'Economics', 'code': 'ECO', 'hod': 'Prof. Simisola Adeniyi', 'hod_email': 'hod.eco@university.edu'},
        {'name': 'Political Science', 'code': 'POL', 'hod': 'Dr. Ibrahim Mohammed', 'hod_email': 'hod.pol@university.edu'},
    ],
}

# Course Data by Department
COURSES_DATA = {
    'CSC': [
        {'code': 'CSC101', 'title': 'Introduction to Programming', 'credits': 3, 'level': '100'},
        {'code': 'CSC201', 'title': 'Data Structures', 'credits': 3, 'level': '200'},
        {'code': 'CSC301', 'title': 'Database Systems', 'credits': 3, 'level': '300'},
        {'code': 'CSC401', 'title': 'Software Engineering', 'credits': 3, 'level': '400'},
    ],
    'MTH': [
        {'code': 'MTH101', 'title': 'Calculus I', 'credits': 3, 'level': '100'},
        {'code': 'MTH201', 'title': 'Linear Algebra', 'credits': 3, 'level': '200'},
        {'code': 'MTH301', 'title': 'Real Analysis', 'credits': 3, 'level': '300'},
    ],
    'EEE': [
        {'code': 'EEE101', 'title': 'Circuit Theory', 'credits': 3, 'level': '100'},
        {'code': 'EEE201', 'title': 'Digital Electronics', 'credits': 3, 'level': '200'},
        {'code': 'EEE301', 'title': 'Power Systems', 'credits': 3, 'level': '300'},
    ],
    'ECO': [
        {'code': 'ECO101', 'title': 'Principles of Economics', 'credits': 3, 'level': '100'},
        {'code': 'ECO201', 'title': 'Macroeconomics', 'credits': 3, 'level': '200'},
        {'code': 'ECO301', 'title': 'Econometrics', 'credits': 3, 'level': '300'},
    ],
}

# Nigerian Names
FIRST_NAMES = [
    'Chidi', 'Ngozi', 'Oluwaseun', 'Amina', 'Emeka', 'Fatima', 'Tunde', 'Adaeze',
    'Ibrahim', 'Chiamaka', 'Oluwafemi', 'Zainab', 'Obinna', 'Simisola', 'Usman'
]

LAST_NAMES = [
    'Okonkwo', 'Okafor', 'Balogun', 'Abdullahi', 'Eze', 'Bello', 'Nwachukwu',
    'Oyedele', 'Suleiman', 'Adebayo', 'Mohammed', 'Okeke'
]

LECTURER_FIRST_NAMES = ['Prof. Ade', 'Dr. Nkechi', 'Prof. Olu', 'Dr. Fatima', 'Prof. Emeka']
LECTURER_LAST_NAMES = ['Adewale', 'Okafor', 'Balogun', 'Suleiman', 'Okonkwo']

ASSIGNMENT_TITLES = [
    'Introduction to Programming - Arrays',
    'Data Structures - Sorting Algorithms',
    'Database Design - SQL Queries',
    'Web Development - HTML/CSS/JS',
    'Software Engineering - Requirements',
    'Network Security - Cryptography'
]

def clear_database():
    """Clear all existing data in correct order"""
    print("Clearing existing data...")
    try:
        # Delete in order of dependencies (child tables first)
        db.session.query(LevelPromotionRequest).delete()
        db.session.query(CarryOverCourse).delete()
        db.session.query(StudentAcademicProgress).delete()
        db.session.query(StudentEnrollment).delete()
        db.session.query(Submission).delete()
        db.session.query(Assignment).delete()
        db.session.query(Course).delete()
        db.session.query(Department).delete()
        db.session.query(College).delete()
        db.session.query(Semester).delete()
        db.session.query(AcademicSession).delete()
        db.session.query(VerificationCode).delete()
        db.session.query(LecturerVerification).delete()
        db.session.query(LecturerRegistrationRequest).delete()
        db.session.query(ActivityLog).delete()
        db.session.query(User).delete()
        db.session.commit()
        print("✓ Database cleared!")
    except Exception as e:
        print(f"Warning during clearing: {e}")
        db.session.rollback()

def create_colleges():
    """Create colleges (skip duplicates)"""
    print("Creating colleges...")
    colleges = []
    for uni in UNIVERSITIES:
        existing = College.query.filter_by(code=uni['code']).first()
        if existing:
            print(f"  ⚠️ College {uni['code']} already exists, skipping")
            colleges.append(existing)
        else:
            college = College(
                name=uni['name'],
                code=uni['code'],
                description=f"{uni['name']} - Main Campus",
                dean_name=uni['dean'],
                dean_email=uni['dean_email'],
                created_at=datetime.now()
            )
            db.session.add(college)
            colleges.append(college)
    
    db.session.commit()
    print(f"✓ Created/Found {len(colleges)} colleges")
    return colleges

def create_departments(colleges):
    """Create departments (skip duplicates)"""
    print("Creating departments...")
    departments = []
    college = colleges[0] if colleges else None
    
    for faculty_name, depts in DEPARTMENTS_DATA.items():
        for dept_data in depts:
            existing = Department.query.filter_by(code=dept_data['code']).first()
            if existing:
                print(f"  ⚠️ Department {dept_data['code']} already exists, skipping")
                departments.append(existing)
            else:
                department = Department(
                    name=f"{dept_data['name']} Department",
                    code=dept_data['code'],
                    description=f"Department of {dept_data['name']}",
                    hod_name=dept_data['hod'],
                    hod_email=dept_data['hod_email'],
                    college_id=college.id if college else 1,
                    created_at=datetime.now()
                )
                db.session.add(department)
                departments.append(department)
    
    db.session.commit()
    print(f"✓ Created/Found {len(departments)} departments")
    return departments

def create_academic_sessions():
    """Create academic sessions (skip duplicates)"""
    print("Creating academic sessions...")
    sessions = []
    years = ['2022/2023', '2023/2024', '2024/2025']
    
    for i, year in enumerate(years):
        existing = AcademicSession.query.filter_by(name=year).first()
        if existing:
            print(f"  ⚠️ Academic session {year} already exists, skipping")
            sessions.append(existing)
        else:
            is_current = (i == len(years) - 1)
            session = AcademicSession(
                name=year,
                start_date=datetime(int(year[:4]), 9, 1),
                end_date=datetime(int(year[:4]) + 1, 8, 31),
                is_current=is_current,
                is_active=True,
                created_at=datetime.now()
            )
            db.session.add(session)
            sessions.append(session)
    
    db.session.commit()
    print(f"✓ Created/Found {len(sessions)} academic sessions")
    return sessions

def create_semesters():
    """Create semesters (skip duplicates)"""
    print("Creating semesters...")
    semesters = []
    
    for year in ['2022/2023', '2023/2024', '2024/2025']:
        for sem_type in ['First', 'Second']:
            name = f"{sem_type} Semester {year}"
            existing = Semester.query.filter_by(name=name).first()
            if existing:
                print(f"  ⚠️ Semester {name} already exists, skipping")
                semesters.append(existing)
            else:
                semester = Semester(
                    name=name,
                    academic_year=year,
                    semester_type=sem_type,
                    start_date=datetime(int(year[:4]), 9 if sem_type == 'First' else 2, 1),
                    end_date=datetime(int(year[:4]) + 1, 2 if sem_type == 'First' else 7, 28),
                    registration_deadline=datetime(int(year[:4]), 10, 15) if sem_type == 'First' else datetime(int(year[:4]) + 1, 3, 15),
                    is_current=(year == '2024/2025' and sem_type == 'First'),
                    is_active=True,
                    created_at=datetime.now()
                )
                db.session.add(semester)
                semesters.append(semester)
    
    db.session.commit()
    print(f"✓ Created/Found {len(semesters)} semesters")
    return semesters

def create_admin():
    """Create admin user (skip if exists)"""
    print("Creating admin user...")
    existing = User.query.filter_by(email='admin@submita.edu').first()
    if existing:
        print("  ⚠️ Admin already exists, skipping")
        return existing
    
    admin = User(
        email='admin@submita.edu',
        matric='ADMIN/001',
        name='Dr. Admin User',
        password=PASSWORD_HASH,
        role=UserRole.ADMIN,
        department='Administration',
        college='University Administration',
        verified=True,
        account_active=True,
        email_verified=True,
        email_verified_at=datetime.now(),
        created_at=datetime.now()
    )
    db.session.add(admin)
    db.session.commit()
    print("✓ Admin created")
    return admin

def create_lecturers(departments):
    """Create lecturer users (skip duplicates)"""
    print("Creating lecturers...")
    lecturers = []
    
    for i in range(5):
        email = f'lecturer{i+1}@submita.edu'
        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f"  ⚠️ Lecturer {email} already exists, skipping")
            lecturers.append(existing)
            continue
            
        dept = departments[i % len(departments)]
        lecturer = User(
            email=email,
            matric=f'LEC/{2024+i:04d}',
            name=f'{LECTURER_FIRST_NAMES[i]} {LECTURER_LAST_NAMES[i]}',
            password=PASSWORD_HASH,
            role=UserRole.LECTURER,
            department=dept.name,
            college=dept.college_ref.name if dept.college_ref else 'College of Natural Sciences',
            verified=True,
            account_active=True,
            email_verified=True,
            email_verified_at=datetime.now(),
            created_at=datetime.now(),
            department_id=dept.id,
            college_id=dept.college_id
        )
        db.session.add(lecturer)
        lecturers.append(lecturer)
    
    db.session.commit()
    print(f"✓ Created/Found {len(lecturers)} lecturers")
    return lecturers

def create_students(departments, academic_sessions):
    """Create student users (skip duplicates)"""
    print("Creating students...")
    students = []
    levels = ['100', '200', '300', '400']
    
    for i in range(30):  # 30 students
        email = f'student{i+1}@submita.edu'
        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f"  ⚠️ Student {email} already exists, skipping")
            students.append(existing)
            continue
            
        first_name = FIRST_NAMES[i % len(FIRST_NAMES)]
        last_name = LAST_NAMES[i % len(LAST_NAMES)]
        dept = departments[i % len(departments)]
        level = levels[i % 4]
        
        # Calculate CGPA
        base_cgpa = random.uniform(2.0, 4.5)
        credits_earned = random.randint(30, 120)
        
        student = User(
            email=email,
            matric=f'STU/{2024+i:04d}',
            name=f'{first_name} {last_name}',
            password=PASSWORD_HASH,
            role=UserRole.STUDENT,
            department=dept.name,
            college=dept.college_ref.name if dept.college_ref else 'College of Natural Sciences',
            level=level,
            current_level=level,
            student_id=f'STU-{2024+i:05d}',
            verified=True,
            account_active=True,
            email_verified=True,
            email_verified_at=datetime.now(),
            enrollment_year='2024',
            expected_graduation_year='2028',
            program_duration=4,
            academic_standing='good' if base_cgpa >= 2.0 else 'probation',
            cgpa=round(base_cgpa, 2),
            total_credits_earned=credits_earned,
            total_credits_attempted=credits_earned + random.randint(0, 15),
            auto_promotion_enabled=True,
            created_at=datetime.now() - timedelta(days=random.randint(0, 365)),
            department_id=dept.id,
            college_id=dept.college_id
        )
        db.session.add(student)
        students.append(student)
    
    # Flush to get IDs
    db.session.flush()
    
    # Create progress records
    for student in students:
        if student.id:  # Only if student was newly created
            current_session = academic_sessions[-1]
            # Check if progress record already exists
            existing_progress = StudentAcademicProgress.query.filter_by(
                student_id=student.id,
                academic_session_id=current_session.id
            ).first()
            
            if not existing_progress:
                progress = StudentAcademicProgress(
                    student_id=student.id,
                    current_level=student.current_level,
                    starting_level='100',
                    academic_session_id=current_session.id,
                    last_promotion_date=datetime.now() - timedelta(days=random.randint(0, 180)),
                    next_promotion_date=datetime.now() + timedelta(days=random.randint(30, 180)),
                    promotion_status='active' if student.cgpa >= 2.0 else 'on_hold',
                    cumulative_gpa=student.cgpa,
                    total_credits_earned=student.total_credits_earned,
                    total_credits_attempted=student.total_credits_attempted,
                    academic_standing=student.academic_standing,
                    created_at=datetime.now()
                )
                db.session.add(progress)
    
    db.session.commit()
    print(f"✓ Created/Found {len(students)} students")
    return students

def create_courses(departments, lecturers):
    """Create courses (skip duplicates)"""
    print("Creating courses...")
    courses = []
    academic_year = '2024/2025'
    
    for dept in departments:
        dept_code = dept.code
        if dept_code in COURSES_DATA:
            for course_data in COURSES_DATA[dept_code]:
                # Check for duplicate
                existing = Course.query.filter_by(
                    code=course_data['code'],
                    academic_year=academic_year
                ).first()
                
                if existing:
                    print(f"  ⚠️ Course {course_data['code']} already exists, skipping")
                    courses.append(existing)
                else:
                    lecturer = random.choice(lecturers)
                    course = Course(
                        code=course_data['code'],
                        title=course_data['title'],
                        description=f"Course in {course_data['title']}",
                        credits=course_data['credits'],
                        level=course_data['level'],
                        semester=random.choice(['First', 'Second']),
                        academic_year=academic_year,
                        is_active=True,
                        department_id=dept.id,
                        college_id=dept.college_id,
                        lecturer_id=lecturer.id,
                        created_at=datetime.now() - timedelta(days=random.randint(0, 60))
                    )
                    db.session.add(course)
                    courses.append(course)
    
    db.session.commit()
    print(f"✓ Created/Found {len(courses)} courses")
    return courses

def create_assignments(lecturers, courses):
    """Create assignments (skip duplicates)"""
    print("Creating assignments...")
    assignments = []
    
    for i, course in enumerate(courses[:20]):  # Limit to 20 assignments
        lecturer = random.choice(lecturers)
        deadline = datetime.now() + timedelta(days=random.randint(5, 25))
        total_points = random.choice([20, 30, 40, 50, 100])
        
        # Check for duplicate
        existing = Assignment.query.filter_by(
            title=f"{random.choice(ASSIGNMENT_TITLES)} - {course.code}",
            course_code=course.code
        ).first()
        
        if existing:
            print(f"  ⚠️ Assignment for {course.code} already exists, skipping")
            assignments.append(existing)
        else:
            assignment = Assignment(
                title=f"{random.choice(ASSIGNMENT_TITLES)} - {course.code}",
                course_code=course.code,
                course_title=course.title,
                description=f"Complete all questions.\nDeadline: {deadline.strftime('%Y-%m-%d')}\nPoints: {total_points}",
                questions="Answer all questions thoroughly.",
                instructions="Submit as PDF.",
                deadline=deadline,
                total_points=total_points,
                target_level=course.level,
                target_semester=course.semester,
                target_academic_year='2024/2025',
                is_published=True,
                published_at=datetime.now() - timedelta(days=random.randint(1, 10)),
                created_by=lecturer.id,
                created_at=datetime.now() - timedelta(days=random.randint(1, 15)),
                course_id=course.id,
                target_department_id=course.department_id,
                target_course_id=course.id
            )
            db.session.add(assignment)
            assignments.append(assignment)
    
    db.session.commit()
    print(f"✓ Created/Found {len(assignments)} assignments")
    return assignments

def create_submissions(students, assignments):
    """Create submissions (skip duplicates)"""
    print("Creating submissions...")
    submissions = []
    
    for student in students[:20]:  # First 20 students
        for assignment in assignments[:10]:  # First 10 assignments
            # Check if submission already exists
            existing = Submission.query.filter_by(
                student_id=student.id,
                assignment_id=assignment.id
            ).first()
            
            if existing:
                continue
                
            if random.random() < 0.6:  # 60% submission rate
                submitted_at = assignment.created_at + timedelta(days=random.randint(1, 10))
                is_late = submitted_at > assignment.deadline
                
                submission = Submission(
                    assignment_id=assignment.id,
                    student_id=student.id,
                    content=f"Submission by {student.name}",
                    file_path=f"/submissions/{student.id}_{assignment.id}.pdf",
                    original_filename=f"{assignment.course_code}_submission.pdf",
                    file_type='pdf',
                    submitted_at=submitted_at,
                    is_late=is_late,
                    late_penalty_applied=10.0 if is_late else 0.0,
                    is_draft=False
                )
                
                # 50% graded
                if random.random() < 0.5:
                    submission.grade = round(random.uniform(40, 100), 1)
                    submission.feedback = "Good work! Keep it up."
                
                db.session.add(submission)
                submissions.append(submission)
    
    db.session.commit()
    print(f"✓ Created {len(submissions)} submissions")
    return submissions

def generate_statistics():
    """Generate and display statistics"""
    print("\n" + "="*70)
    print("DATABASE SEEDING COMPLETE!")
    print("="*70)
    
    stats = {
        '👑 Admins': User.query.filter_by(role=UserRole.ADMIN).count(),
        '👨‍🏫 Lecturers': User.query.filter_by(role=UserRole.LECTURER).count(),
        '👨‍🎓 Students': User.query.filter_by(role=UserRole.STUDENT).count(),
        '🏛️ Colleges': College.query.count(),
        '📚 Departments': Department.query.count(),
        '📖 Courses': Course.query.count(),
        '📝 Assignments': Assignment.query.count(),
        '📎 Submissions': Submission.query.count(),
        '📊 Enrollments': StudentEnrollment.query.count(),
        '📅 Academic Sessions': AcademicSession.query.count(),
        '📆 Semesters': Semester.query.count(),
    }
    
    print("\n📊 DATABASE STATISTICS:")
    print("-" * 50)
    for key, value in stats.items():
        print(f"  {key:25}: {value}")
    
    print("\n🔐 LOGIN CREDENTIALS (Password for ALL: password123)")
    print("-" * 50)
    print("  📧 Admin:     admin@submita.edu")
    print("  📧 Lecturer:  lecturer1@submita.edu")
    print("  📧 Student:   student1@submita.edu")
    print("="*70)

def main():
    """Main seeding function"""
    print("="*70)
    print("🚀 SUBMITA DATABASE SEEDER")
    print("="*70)
    print("\nThis script will populate your database with test data.")
    print("All passwords are set to: password123")
    print("\nStarting seeding process...\n")
    
    with app.app_context():
        try:
            # Create all data (duplicates will be skipped)
            colleges = create_colleges()
            departments = create_departments(colleges)
            academic_sessions = create_academic_sessions()
            semesters = create_semesters()
            
            admin = create_admin()
            lecturers = create_lecturers(departments)
            students = create_students(departments, academic_sessions)
            
            courses = create_courses(departments, lecturers)
            assignments = create_assignments(lecturers, courses)
            submissions = create_submissions(students, assignments)
            
            generate_statistics()
            
            print("\n✅ SEEDING COMPLETED SUCCESSFULLY!")
            print("\n🎯 You can now run the application: python app.py")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error during seeding: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    main()