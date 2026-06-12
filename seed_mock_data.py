#!/usr/bin/env python3
"""
Mock Data Seeder for Submita Platform
Run this script to populate the database with test data
"""

import os
import sys
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, UserRole, Assignment, Submission, Course, Department, College

# Configuration
PASSWORD_HASH = generate_password_hash('password123')

# Nigerian universities data
UNIVERSITIES = [
    {'name': 'University of Lagos', 'code': 'UNILAG'},
    {'name': 'University of Ibadan', 'code': 'UI'},
    {'name': 'Obafemi Awolowo University', 'code': 'OAU'},
]

FACULTIES = [
    {'name': 'Faculty of Science', 'code': 'SCI'},
    {'name': 'Faculty of Engineering', 'code': 'ENG'},
    {'name': 'Faculty of Social Sciences', 'code': 'SSC'},
]

DEPARTMENTS = {
    'Faculty of Science': [
        {'name': 'Computer Science', 'code': 'CSC'},
        {'name': 'Mathematics', 'code': 'MTH'},
        {'name': 'Physics', 'code': 'PHY'},
        {'name': 'Chemistry', 'code': 'CHM'},
    ],
    'Faculty of Engineering': [
        {'name': 'Electrical Engineering', 'code': 'EEE'},
        {'name': 'Mechanical Engineering', 'code': 'MEE'},
        {'name': 'Civil Engineering', 'code': 'CVE'},
    ],
    'Faculty of Social Sciences': [
        {'name': 'Economics', 'code': 'ECO'},
        {'name': 'Political Science', 'code': 'POL'},
        {'name': 'Sociology', 'code': 'SOC'},
    ]
}

# Course data
COURSES_DATA = {
    'CSC': [
        {'code': 'CSC101', 'title': 'Introduction to Programming', 'credits': 3},
        {'code': 'CSC201', 'title': 'Data Structures', 'credits': 3},
        {'code': 'CSC301', 'title': 'Database Management Systems', 'credits': 3},
        {'code': 'CSC401', 'title': 'Software Engineering', 'credits': 3},
    ],
    'MTH': [
        {'code': 'MTH101', 'title': 'Calculus I', 'credits': 3},
        {'code': 'MTH201', 'title': 'Linear Algebra', 'credits': 3},
        {'code': 'MTH301', 'title': 'Differential Equations', 'credits': 3},
    ],
    'EEE': [
        {'code': 'EEE101', 'title': 'Circuit Theory', 'credits': 3},
        {'code': 'EEE201', 'title': 'Electronics', 'credits': 3},
        {'code': 'EEE301', 'title': 'Power Systems', 'credits': 3},
    ],
}

# Nigerian names
FIRST_NAMES = [
    'Chidi', 'Ngozi', 'Oluwaseun', 'Amina', 'Emeka', 'Fatima', 'Tunde', 'Adaeze',
    'Ibrahim', 'Chiamaka', 'Oluwafemi', 'Zainab', 'Obinna', 'Simisola', 'Usman',
    'Chinwe', 'Segun', 'Rahma', 'Ifeanyi', 'Khadija'
]

LAST_NAMES = [
    'Okonkwo', 'Okafor', 'Balogun', 'Abdullahi', 'Eze', 'Bello', 'Nwachukwu',
    'Oyedele', 'Suleiman', 'Adebayo', 'Mohammed', 'Okeke', 'Ogunlesi', 'Hassan'
]

LECTURER_FIRST_NAMES = ['Prof. Ade', 'Dr. Nkechi', 'Prof. Olu', 'Dr. Fatima', 'Prof. Emeka', 'Dr. Grace']
LECTURER_LAST_NAMES = ['Adewale', 'Okafor', 'Balogun', 'Suleiman', 'Okonkwo', 'Oyedele']

ASSIGNMENT_TITLES = [
    'Introduction to Programming - Arrays and Functions',
    'Data Structures - Sorting Algorithms Implementation',
    'Database Design - SQL Queries and Normalization',
    'Web Development - HTML/CSS/JavaScript Project',
    'Software Engineering - Requirements Specification Document',
    'Network Security - Cryptography Assignment',
    'Operating Systems - Process Scheduling Simulation',
    'Machine Learning - Linear Regression Implementation'
]

ASSIGNMENT_DESCRIPTIONS = [
    """Implement the following programming exercises:
    1. Write a function to find the maximum element in an array
    2. Implement binary search algorithm
    3. Create a program to sort an array using bubble sort
    
    Submit your code with proper comments and test cases.
    Deadline: {deadline}
    Total Points: {points}""",
    
    """Implement the following sorting algorithms:
    - Quick Sort
    - Merge Sort
    - Heap Sort
    
    Compare their time complexities and provide analysis.
    Submit code and a report (PDF).
    Deadline: {deadline}
    Total Points: {points}"""
]

def clear_database():
    """Clear all existing data"""
    print("Clearing existing data...")
    try:
        db.session.query(Submission).delete()
        db.session.query(Assignment).delete()
        db.session.query(Course).delete()
        db.session.query(Department).delete()
        db.session.query(College).delete()
        db.session.query(User).delete()
        db.session.commit()
        print("✓ Database cleared!")
    except Exception as e:
        print(f"Error clearing database: {e}")
        db.session.rollback()

def create_colleges_and_departments():
    """Create colleges and departments"""
    print("Creating colleges and departments...")
    colleges = []
    departments = []
    
    for uni in UNIVERSITIES:
        college = College(
            name=uni['name'],
            code=uni['code'],
            description=f"{uni['name']} - Main Campus",
            dean_name=f"Dean of {uni['name']}",
            dean_email=f"dean@{uni['code'].lower()}.edu"
        )
        db.session.add(college)
        colleges.append(college)
        
    db.session.commit()
    
    # Create departments for each faculty
    for faculty_name, depts in DEPARTMENTS.items():
        for dept_data in depts:
            department = Department(
                name=f"{dept_data['name']} Department",
                code=dept_data['code'],
                description=f"Department of {dept_data['name']}",
                hod_name=f"HOD of {dept_data['name']}",
                hod_email=f"hod.{dept_data['code'].lower()}@university.edu",
                college_id=colleges[0].id
            )
            db.session.add(department)
            departments.append(department)
    
    db.session.commit()
    print(f"✓ Created {len(colleges)} colleges and {len(departments)} departments")
    return colleges, departments

def create_admin():
    """Create admin user"""
    print("Creating admin user...")
    admin = User(
        email='admin@submita.edu',
        matric='ADMIN001',
        name='Admin User',
        password=PASSWORD_HASH,
        role=UserRole.ADMIN,
        verified=True,
        account_active=True,
        email_verified=True,
        created_at=datetime.now()
    )
    db.session.add(admin)
    return admin

def create_lecturers(departments):
    """Create lecturer users"""
    print("Creating lecturers...")
    lecturers = []
    for i in range(6):
        dept = departments[i % len(departments)]
        lecturer = User(
            email=f'lecturer{i+1}@submita.edu',
            matric=f'LEC{i+1:04d}',
            name=f'{LECTURER_FIRST_NAMES[i]} {LECTURER_LAST_NAMES[i]}',
            password=PASSWORD_HASH,
            role=UserRole.LECTURER,
            department=dept.name,
            college=dept.college_ref.name if dept.college_ref else 'College of Natural Sciences',
            verified=True,
            account_active=True,
            email_verified=True,
            created_at=datetime.now(),
            department_id=dept.id
        )
        db.session.add(lecturer)
        lecturers.append(lecturer)
    
    db.session.commit()
    print(f"✓ Created {len(lecturers)} lecturers")
    return lecturers

def create_students(departments):
    """Create student users"""
    print("Creating students...")
    students = []
    levels = ['100', '200', '300', '400']
    
    for i in range(30):
        first_name = FIRST_NAMES[i % len(FIRST_NAMES)]
        last_name = LAST_NAMES[i % len(LAST_NAMES)]
        dept = departments[i % len(departments)]
        level = random.choice(levels)
        
        student = User(
            email=f'student{i+1}@submita.edu',
            matric=f'STU/{2024+i:03d}',
            name=f'{first_name} {last_name}',
            password=PASSWORD_HASH,
            role=UserRole.STUDENT,
            department=dept.name,
            college=dept.college_ref.name if dept.college_ref else 'College of Natural Sciences',
            level=level,
            current_level=level,
            student_id=f'STU-{2024+i:04d}',
            verified=True,
            account_active=True,
            email_verified=True,
            enrollment_year='2024',
            expected_graduation_year='2028',
            program_duration=4,
            academic_standing='good',
            cgpa=round(random.uniform(2.0, 4.5), 2),
            total_credits_earned=random.randint(30, 120),
            total_credits_attempted=random.randint(30, 130),
            created_at=datetime.now(),
            department_id=dept.id
        )
        db.session.add(student)
        students.append(student)
    
    db.session.commit()
    print(f"✓ Created {len(students)} students")
    return students

def create_courses(departments, lecturers):
    """Create courses"""
    print("Creating courses...")
    courses = []
    semesters = ['First', 'Second']
    
    for dept in departments:
        dept_code = dept.code
        if dept_code in COURSES_DATA:
            for course_data in COURSES_DATA[dept_code]:
                for level in ['100', '200', '300', '400']:
                    for semester in semesters:
                        lecturer = random.choice(lecturers)
                        course = Course(
                            code=course_data['code'],
                            title=course_data['title'],
                            description=f"Comprehensive course in {course_data['title']}",
                            credits=course_data['credits'],
                            level=level,
                            semester=semester,
                            academic_year='2024/2025',
                            is_active=True,
                            department_id=dept.id,
                            college_id=dept.college_id,
                            lecturer_id=lecturer.id,
                            created_at=datetime.now()
                        )
                        db.session.add(course)
                        courses.append(course)
    
    db.session.commit()
    print(f"✓ Created {len(courses)} courses")
    return courses

def create_assignments(lecturers, courses):
    """Create assignments"""
    print("Creating assignments...")
    assignments = []
    
    for i in range(20):
        lecturer = random.choice(lecturers)
        course = random.choice(courses)
        deadline = datetime.now() + timedelta(days=random.randint(3, 21))
        total_points = random.choice([20, 30, 40, 50, 100])
        
        assignment = Assignment(
            title=random.choice(ASSIGNMENT_TITLES) + f" (Week {i%8 + 1})",
            course_code=course.code,
            course_title=course.title,
            description=random.choice(ASSIGNMENT_DESCRIPTIONS).format(deadline=deadline.strftime('%Y-%m-%d'), points=total_points),
            questions=f"Answer all questions in the assignment.\n\nTotal Points: {total_points}",
            instructions="Submit your work as a PDF file. Include your matric number and name.",
            deadline=deadline,
            total_points=total_points,
            target_level=random.choice(['100', '200', '300', '400']),
            target_semester=random.choice(['First', 'Second']),
            target_academic_year='2024/2025',
            is_published=True,
            published_at=datetime.now() - timedelta(days=random.randint(1, 7)),
            late_submission_penalty=10.0,
            created_by=lecturer.id,
            created_at=datetime.now() - timedelta(days=random.randint(1, 10)),
            course_id=course.id,
            target_department_id=course.department_id,
            target_course_id=course.id
        )
        db.session.add(assignment)
        assignments.append(assignment)
    
    db.session.commit()
    print(f"✓ Created {len(assignments)} assignments")
    return assignments

def create_submissions(students, assignments):
    """Create submissions for students"""
    print("Creating submissions...")
    submissions = []
    
    for student in students:
        # Each student submits to 5-10 assignments
        num_submissions = random.randint(5, min(12, len(assignments)))
        selected_assignments = random.sample(assignments, num_submissions)
        
        for assignment in selected_assignments:
            # 70% submission rate
            if random.random() < 0.7:
                submitted_at = assignment.created_at + timedelta(days=random.randint(1, 10))
                is_late = submitted_at > assignment.deadline
                
                submission = Submission(
                    assignment_id=assignment.id,
                    student_id=student.id,
                    content=f"Submitted by {student.name}\n\nMatric: {student.matric}\nCourse: {assignment.course_code}\n\nThis is my submission for {assignment.title}.",
                    file_path=f"/submissions/{student.id}_{assignment.id}_submission_{random.randint(1000, 9999)}.pdf",
                    original_filename=f"submission_{assignment.course_code}.pdf",
                    file_type='pdf',
                    submitted_at=submitted_at,
                    is_late=is_late,
                    late_penalty_applied=10.0 if is_late else 0.0,
                    is_draft=False,
                    resubmission_count=random.randint(0, 2)
                )
                
                # 50% of submissions are graded
                if random.random() < 0.5:
                    submission.grade = round(random.uniform(40, 100), 1)
                    submission.feedback = random.choice([
                        "Excellent work! Great understanding of concepts.",
                        "Good effort. Some areas need improvement.",
                        "Satisfactory. Keep practicing.",
                        "Well done! Could use more detail.",
                        "Good submission. Please follow formatting guidelines."
                    ])
                
                db.session.add(submission)
                submissions.append(submission)
    
    db.session.commit()
    print(f"✓ Created {len(submissions)} submissions")
    return submissions

def generate_statistics():
    """Generate and display statistics"""
    print("\n" + "="*60)
    print("DATABASE SEEDING COMPLETE!")
    print("="*60)
    
    stats = {
        'Admins': User.query.filter_by(role=UserRole.ADMIN).count(),
        'Lecturers': User.query.filter_by(role=UserRole.LECTURER).count(),
        'Students': User.query.filter_by(role=UserRole.STUDENT).count(),
        'Colleges': College.query.count(),
        'Departments': Department.query.count(),
        'Courses': Course.query.count(),
        'Assignments': Assignment.query.count(),
        'Submissions': Submission.query.count(),
    }
    
    print("\n📊 Database Statistics:")
    print("-" * 40)
    for key, value in stats.items():
        print(f"  {key:15}: {value}")
    
    print("\n🔐 Login Credentials (All users):")
    print("-" * 40)
    print("  Password: password123")
    print("\n  Sample Logins:")
    print("  • Admin:     admin@submita.edu")
    print("  • Lecturer:  lecturer1@submita.edu")
    print("  • Student:   student1@submita.edu")
    print("="*60)

def main():
    """Main seeding function"""
    print("🚀 Starting database seeding...")
    print("="*60)
    
    with app.app_context():
        try:
            # Clear existing data
            clear_database()
            
            # Create all mock data
            colleges, departments = create_colleges_and_departments()
            admin = create_admin()
            lecturers = create_lecturers(departments)
            students = create_students(departments)
            courses = create_courses(departments, lecturers)
            assignments = create_assignments(lecturers, courses)
            submissions = create_submissions(students, assignments)
            
            # Show statistics
            generate_statistics()
            
            print("\n✅ Seeding completed successfully!")
            print("You can now run the application and log in with any test account.")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error during seeding: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    main()