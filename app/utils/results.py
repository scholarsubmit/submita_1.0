"""
app/utils/results.py — compiles a result sheet across every assignment
that shares a course_code, instead of the per-assignment CSV export
that already existed. This is the "auto result compilation" piece.

Design choice on incomplete data: a student's total/percentage is only
computed once every assignment in the course has been graded FOR THEM.
Showing a misleading partial percentage (as if ungraded work = zero)
would be actively wrong, not just incomplete — so those rows are marked
"Incomplete" instead of silently undercutting a student's real standing.
"""
from app.models import Submission


def compile_course_results(assignments):
    """
    assignments: list of Assignment objects (all assumed to share one
    course_code — callers are responsible for that scoping).

    Returns a dict:
      {
        'assignments': [assignment, ...] (sorted by deadline),
        'total_possible': int,
        'rows': [
          {
            'student': User,
            'cells': {assignment_id: {'status': 'graded'|'pending'|'missing', 'grade': float|None}},
            'total_earned': float|None,
            'percentage': float|None,   # None if incomplete
          }, ...
        ] (sorted by percentage desc, incompletes last)
      }
    """
    assignments = sorted(assignments, key=lambda a: a.deadline)
    total_possible = sum(a.total_points for a in assignments)

    # Gather every student who submitted to ANY assignment in this course.
    students_by_id = {}
    submissions_by_assignment = {}
    for a in assignments:
        subs = Submission.query.filter_by(assignment_id=a.id).all()
        submissions_by_assignment[a.id] = {s.student_id: s for s in subs}
        for s in subs:
            students_by_id[s.student_id] = s.student

    rows = []
    for student_id, student in students_by_id.items():
        cells = {}
        earned = 0.0
        complete = True

        for a in assignments:
            sub = submissions_by_assignment[a.id].get(student_id)
            if sub is None:
                cells[a.id] = {'status': 'missing', 'grade': None}
                complete = False
            elif sub.grade is None:
                cells[a.id] = {'status': 'pending', 'grade': None}
                complete = False
            else:
                cells[a.id] = {'status': 'graded', 'grade': sub.grade}
                earned += sub.grade

        rows.append({
            'student': student,
            'cells': cells,
            'total_earned': earned if complete else None,
            'percentage': round((earned / total_possible) * 100, 1) if (complete and total_possible) else None,
        })

    rows.sort(key=lambda r: (r['percentage'] is None, -(r['percentage'] or 0)))

    return {'assignments': assignments, 'rows': rows, 'total_possible': total_possible}
