# Submita v2 — Phase 1 + Phase 2

Phase 1 was the foundation (auth, security, onboarding). **Phase 2 adds
real dashboards for all three roles, plus enough of the assignment
lifecycle to make them meaningful:** creation, publishing, submission,
and manual grading. AI grading, plagiarism detection, and auto result
compilation are still the next phase — the data model already has the
`plagiarism_score` column waiting for that work.

## What's working right now (Phase 1 + 2 combined)

**Auth & security** (Phase 1): student registration with matric
validation, email verification, lockout-protected login, full lecturer
onboarding chain (request → admin approval → invite code → redemption),
CSRF + rate limiting + security headers everywhere.

**Dashboards** (Phase 2, new):
- Student: **upcoming deadlines sorted by urgency** (red/amber/green),
  recent submissions with grades, stats
- Lecturer: assignment list with submission/pending counts, recent
  submissions queue, one-click access to grading
- Admin: platform stats, pending lecturer requests, recently registered
  users
- **Collapsible sidebar** on all three (state persists across visits),
  responsive down to mobile (becomes a slide-out drawer)
- **Live activity feed** in the notification bell, polling every 30
  seconds — lecturers see new submissions as they land, students see
  grades as they're posted, without refreshing

**Assignments** (Phase 2, new, minimal but real):
- Lecturers create/publish assignments targeted at a department + level
- Students see only assignments matching their own department/level,
  automatically hidden once submitted
- Manual grading with feedback — AI-assisted grading plugs in here next

I ran the **entire lifecycle** through the Flask test client before
handing this over: lecturer creates an assignment → it appears on the
right students' dashboards → student submits → it shows up in the
lecturer's live feed → lecturer grades it → the grade appears on the
student's dashboard AND in their activity feed. All of it works.

# Submita v2 — Phase 1 + 2 + 3

Phase 1: auth, security, onboarding. Phase 2: real dashboards with
sidebars and live data. **Phase 3 (this update) adds AI grading,
plagiarism detection, file uploads, and CSV result export** — the
last major pieces from the original brief.

## What's new in Phase 3

- **AI grading suggestions (Claude API)** — on any submission's grade
  page, a lecturer can click "Get AI grading suggestion" to have Claude
  assess the submission against the assignment's instructions and
  suggest a score, feedback, strengths, and weaknesses. **This never
  writes a grade by itself** — it's a suggestion that pre-fills the
  grading form, which the lecturer reviews, edits, and explicitly saves.
  If `ANTHROPIC_API_KEY` isn't set, the button just says AI grading is
  unavailable and manual grading works exactly as before — nothing
  breaks.
- **Plagiarism detection** — runs automatically the instant a student
  submits, comparing their submission's text against every *other*
  submission for that *same assignment* (per your scoping decision —
  not a general web search). Uses sequence-matching + phrase-shingle
  similarity, the same proven approach as your original app, ported
  and fixed. **I caught and fixed a real bug while testing this**:
  Python's `SequenceMatcher` has an `autojunk` heuristic that made
  similarity scores asymmetric (two near-identical texts were scoring
  78% one direction and 43% the other) — now fixed and verified
  symmetric.
- **File uploads for submissions** — students can now attach a file
  instead of (or alongside) typed content. Same security model as your
  original app: extension whitelist, size limit, and a byte-signature
  scan that rejects files smuggling script/executable content.
- **CSV result export ("auto result compilation")** — on any
  assignment's management page, "Export results" downloads a CSV with
  every student's matric number, grade, plagiarism score, late status,
  and feedback — ready to paste into a gradebook or send to the
  exams office.
- **Password reset** — added this myself, unprompted: "super active
  security" was explicit in the brief, and a missing "forgot password"
  flow is a real gap for a production auth system (it either locks
  users out permanently or pushes them toward insecure workarounds).
  Same hashed-token pattern as email verification: a random token is
  emailed as a link, only its hash is ever stored, it expires in 30
  minutes, and it's single-use. Tested end-to-end: old password stops
  working immediately, new password works, and the link can't be
  reused a second time.

I tested all of this myself before handing it over, including
deliberately trying to break it: two students submitting near-identical
text (correctly flagged, and the asymmetry bug caught and fixed),
a mocked AI grading call rendering correctly into the form, a real file
upload persisting to disk and being retrievable, a `.exe` upload being
rejected by the extension whitelist, and a file containing
`<?php system(...)` being rejected by the content scan.

## Setup — one new step

Same as before, but now also set `ANTHROPIC_API_KEY` in `.env` (get one
at https://console.anthropic.com/settings/keys) if you want AI grading
active. Everything else works identically without it.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then fill in real values, including ANTHROPIC_API_KEY
python seed_academic_structure.py
python create_admin.py
python run.py
```

**Note on `psycopg2-binary`:** it's deliberately in a separate
`requirements-postgres.txt`, not the main `requirements.txt`. You don't
need it for local development (SQLite, the default) — only install it
if you're connecting to a real PostgreSQL database:
```bash
pip install -r requirements-postgres.txt
```
On Windows this can fail with a "Microsoft C++ Build Tools required"
error if there's no prebuilt wheel for your exact Python version. If
you're deploying to Render or another Linux host, that's not a problem
you need to solve locally at all — it'll install cleanly on their
Linux build servers regardless.

## Cross-assignment result compilation (new this update)

On top of the per-assignment CSV export, lecturers now have a
**"Course Results"** page (sidebar → Course Results) that compiles
every assignment sharing a course code — scoped to the same semester/
academic year, which is why those fields were added to `Assignment`
specifically: a course taught across two different semesters should
never have its results mixed together — into one table per student:

- A column per assignment, a running total, and a percentage
- **A student with any missing or ungraded work is marked
  "Incomplete" rather than shown a misleadingly low score.** Silently
  treating ungraded work as zero would actively misrepresent a
  student's standing, not just show incomplete data — deliberate choice,
  see `app/utils/results.py`.
- Exportable as one compiled CSV, verified to match the web table exactly

Tested end-to-end: two assignments in one course, one student who
completed both (correctly shows 93%), one who only did one (correctly
shows "Incomplete" instead of a deceptive 40/100).

## Landing page (also new this update)

Real marketing page at `/`, built around the same ID-badge component
used throughout the app (an actual floating student-ID visual in the
hero, in your matric format), a genuine 4-step registration sequence,
and a dedicated security section calling out the lecturer-invite chain
specifically — that's the part of the brief most focused on preventing
impersonation, so it gets called out by name rather than folded into a
generic "secure" bullet point.

## Security & admin additions (new this update)

- **System-generated staff IDs** — admins no longer type in a staff ID
  when approving a lecturer or sending a direct invite. The system
  generates one in the format `LEC/SUB/YY/NNNNAA` (e.g.
  `LEC/SUB/26/0720AB`) and guarantees it's unique before issuing it —
  tested end-to-end, format confirmed correct via regex.
- **Password show/hide toggle** — every password field across the app
  (login, register, reset password, lecturer onboarding) now has an eye
  icon to reveal/hide what you typed.
- **Matric/staff ID show/hide toggle** — the ID badge shown on
  dashboards can be masked with one click (useful if someone's looking
  over your shoulder). The preference persists across the whole site
  via localStorage, not just the current page.
- **Admin: user management** — a real "All Users" page now exists
  (search/filter by name, email, matric, staff ID, or role), with
  deactivate/reactivate and delete actions. **Deliberate safety guard**:
  deleting an account that has any assignments or submissions tied to
  it is blocked — that would destroy real grades and submitted work.
  The UI points admins at deactivation instead, which removes access
  without erasing history. Tested both paths: delete succeeds for a
  clean account, blocked correctly for one with academic records.
- **Assignment questions** — `create_assignment` now has an actual
  "Questions" section: type them directly, upload a file in **any
  format up to 5MB** (executables/scripts specifically blocked
  regardless of format), or both. At least one is required. Students
  see the typed questions and/or a download link on both the
  assignment view and submit pages. The download route checks that the
  requester is the assignment's own lecturer, an admin, or a student
  whose department and level actually match the assignment's target —
  tested and confirmed an unrelated-department student gets a 403.

## ⚠️ Still open

1. **Matric format** — still unconfirmed, built against `MOUAU/CSC/22/012345`.
2. **Logo / PWA icons** — still placeholders (the hero badge doesn't need one, but the navbar mark and PWA install icon do).
3. **Fonts** — still system-font fallback.
4. **`datetime.utcnow()` deprecation** — still tracked tech debt, not urgent.
5. **Profile editing** — still no in-app way to update your own info.



## Project structure

```
app/
  __init__.py         # application factory — wires everything together
  extensions.py        # db, login_manager, csrf, limiter — created once
  models.py             # every database table + security-critical logic
  blueprints/
    auth.py             # register, login, verify, lecturer onboarding
    admin.py             # lecturer request review (Phase 1 slice only)
    dashboard.py         # role-based dashboard dispatch (placeholders)
    api.py               # public read-only JSON endpoints (departments)
  utils/
    security.py          # matric/password validation, sanitization
    email.py              # SMTP sending + templated messages
templates/            # organized by role/section, mirrors blueprints/
static/
  css/main.css          # the whole design system, no build step
  js/theme.js            # light/dark toggle
  js/pwa.js               # service worker registration + install prompt
  manifest.json, sw.js   # PWA
config.py              # all settings — actually loaded this time
seed_academic_structure.py
create_admin.py
run.py
```

## Next phase

Once you've confirmed the matric format and dropped in real icons/fonts,
next up per our build order: the real student/lecturer/admin dashboards
with live data and the sidebar navigation, then assignment
creation/submission, then AI grading (LLM-based, per your choice) and
plagiarism detection, then auto result compilation.
