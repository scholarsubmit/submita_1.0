# Submita — CS Assignment Submission & Plagiarism Platform

## Quick start

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
# Open http://localhost:5000
```

## Demo login credentials

| Role     | Username   | Password  |
|----------|------------|-----------|
| Student  | student1   | pass123   |
| Lecturer | lecturer1  | pass123   |

## Pages & routes

| Route                          | Description                    |
|-------------------------------|--------------------------------|
| `/login`                      | Login page                     |
| `/student`                    | Student assignment list        |
| `/submit/<assignment_id>`     | Submit an assignment           |
| `/student/results`            | Student grades & feedback      |
| `/lecturer`                   | Lecturer dashboard             |
| `/lecturer/submission/<id>`   | Grade a submission             |
| `/lecturer/plagiarism/<id>`   | Full plagiarism report         |
| `/api/submissions`            | JSON API for submissions       |

## Project structure

```
submita/
├── app.py                  # Main Flask app (routes, logic, plagiarism engine)
├── requirements.txt
├── uploads/                # Uploaded student files
└── templates/
    ├── base.html           # Shared layout + green theme
    ├── login.html          # Login page
    ├── student_dashboard.html
    ├── submit.html         # Assignment submission form
    ├── student_results.html
    ├── lecturer_dashboard.html
    ├── submission_detail.html  # Grade & feedback form
    └── plagiarism_report.html  # Side-by-side code comparison
```

## Plagiarism detection

Uses Python's built-in `difflib.SequenceMatcher` for token-level and
line-level similarity comparison. Submissions are compared against all
other submissions in the same assignment automatically on upload.

Similarity thresholds:
- **< 30%** — Low risk (green)
- **30–59%** — Moderate (amber)
- **≥ 60%** — High risk, auto-flagged (red)

## Moving to production

- Replace the in-memory `USERS`, `SUBMISSIONS`, `GRADES` dicts with SQLite or PostgreSQL (use SQLAlchemy)
- Set `SECRET_KEY` from environment variable
- Use a production WSGI server (gunicorn or waitress)
- Add email notifications on submission and grade release
- Store uploaded files in cloud storage (S3, GCS) for scalability
