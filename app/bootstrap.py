"""
app/bootstrap.py — one-time database setup that must run no matter HOW the
app is started.

Why this exists: gunicorn starts the app with `gunicorn run:app`, which
IMPORTS run.py as a module and grabs the `app` object off it — it never
executes run.py's `if __name__ == '__main__':` block. That block was the
ONLY place db.create_all() ran, so on Render (and any other gunicorn/WSGI
deploy) no tables were ever created, which is why every DB-touching route
returned a 500 and why seed_academic_structure.py failed locally with
"no such table: colleges" if run.py hadn't been run first.

Everything in here is idempotent and safe to call on every process start,
every gunicorn worker, every redeploy — each step checks what already
exists before doing anything.
"""
import json
import os

from sqlalchemy import text, inspect as sa_inspect

# ── First-admin credentials ──────────────────────────────────────────
# Only used the very first time the app boots against a fresh database.
# Change the password after logging in.
DEFAULT_ADMIN = {
    'name': 'Scholar Submit',
    'email': 'scholarsubmit1@gmail.com',
    'staff_id': 'SUBMITA001',  # stored uppercase — login normalizes identifiers to upper()
    'password': '1234567890@Me',
}


def bootstrap_database(app, db):
    """Call once, right after db.init_app(app), inside create_app()."""
    with app.app_context():
        # Models must be imported BEFORE create_all(), otherwise their
        # tables are never registered on db.metadata and create_all()
        # silently creates nothing at all (no error — just an empty DB).
        import app.models  # noqa: F401

        try:
            db.create_all()
        except Exception as exc:
            app.logger.error(f'db.create_all() failed: {exc}')
            print(f'❌ db.create_all() failed: {exc}')
            return  # nothing below will work without tables

        _auto_migrate(app, db)
        _seed_academic_structure(app, db)
        _create_default_admin(app, db)


def _auto_migrate(app, db):
    """Adds any column that exists on a model in models.py but is missing
    from the actual database table — generic and automatic, not a
    hardcoded list, so it keeps working as models.py evolves. Existing
    tables can predate a model change (e.g. a table created by an earlier
    deploy before a field was added), so this diffs every mapped table
    against its real columns and patches the gap.

    Added columns are always created NULLable regardless of what the
    model declares, even if the model says nullable=False — an ALTER
    TABLE ... NOT NULL would fail outright on a table that already has
    rows, since there's no way to backfill a real value (e.g. a real
    password hash) automatically. This unblocks the app immediately;
    going forward, backfill any such column for existing rows by hand.
    """
    try:
        inspector = sa_inspect(db.engine)
        existing_tables = set(inspector.get_table_names())
    except Exception as exc:
        print(f'⚠️  Auto-migrate skipped, could not inspect DB: {exc}')
        return

    for table_name, table in db.metadata.tables.items():
        if table_name not in existing_tables:
            continue  # brand-new table — db.create_all() already handled it
        try:
            existing_columns = {c['name'] for c in inspector.get_columns(table_name)}
        except Exception as exc:
            print(f'⚠️  Could not inspect columns for {table_name}: {exc}')
            continue

        for column in table.columns:
            if column.name in existing_columns:
                continue
            try:
                col_type = column.type.compile(dialect=db.engine.dialect)
                default_clause = _default_clause_for(column)
                ddl = f'ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}{default_clause}'
                with db.engine.connect() as conn:
                    conn.execute(text(ddl))
                    conn.commit()
                print(f'✅ Migrated: {table_name}.{column.name} ({col_type})')
            except Exception as exc:
                print(f'⚠️  Could not add {table_name}.{column.name}: {exc}')


def _default_clause_for(column):
    """Best-effort ' DEFAULT ...' SQL fragment so existing rows get a
    sensible backfilled value instead of NULL, when the model clearly
    specifies one (server_default, or a scalar Python-side default like
    `default='First'`). Returns '' when there's nothing safe to use —
    the column is simply added as NULLable with no default in that case."""
    if column.server_default is not None:
        return f' DEFAULT {column.server_default.arg}'

    if column.default is not None and not column.default.is_callable and not column.default.is_sequence:
        value = column.default.arg
        if isinstance(value, str):
            escaped = value.replace("'", "''")
            return f" DEFAULT '{escaped}'"
        if isinstance(value, bool):
            return f' DEFAULT {"TRUE" if value else "FALSE"}'
        if isinstance(value, (int, float)):
            return f' DEFAULT {value}'
        # Enums, datetimes, callables, etc: not safe to inline as a
        # literal — leave the column NULLable with no default instead.
    return ''


def _seed_academic_structure(app, db):
    from app.models import College, Department

    try:
        if College.query.first():
            return  # already seeded, nothing to do
    except Exception as exc:
        print(f'⚠️  Academic structure seed check failed: {exc}')
        return

    try:
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'academic_structure.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        universities = data.get('Universities', [])
        if not universities:
            print('⚠️  Seed skipped: no "Universities" key in academic_structure.json')
            return

        college_count = 0
        dept_count = 0
        for college_data in universities[0].get('colleges', []):
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
        print(f'✅ Seeded {college_count} colleges and {dept_count} departments.')
    except Exception as exc:
        db.session.rollback()
        print(f'⚠️  Academic structure seeding failed: {exc}')


def _create_default_admin(app, db):
    from app.models import User, UserRole
    from app.utils.security import valid_email_format

    email = DEFAULT_ADMIN['email']
    staff_id = DEFAULT_ADMIN['staff_id']

    try:
        exists = User.query.filter(
            db.or_(User.email == email, User.staff_id == staff_id)
        ).first()
        if exists:
            return  # already created — never overwrite an existing account
    except Exception as exc:
        print(f'⚠️  Default admin check failed: {exc}')
        return

    if not valid_email_format(email):
        print(f'⚠️  Default admin not created: "{email}" is not a valid email format.')
        return

    try:
        admin = User(
            role=UserRole.ADMIN,
            name=DEFAULT_ADMIN['name'],
            email=email,
            staff_id=staff_id,
            is_email_verified=True,  # created out-of-band, already trusted
        )
        admin.set_password(DEFAULT_ADMIN['password'])
        db.session.add(admin)
        db.session.commit()
        print(f'✅ Default admin account created: {email} / staff ID {staff_id}')
    except Exception as exc:
        db.session.rollback()
        print(f'⚠️  Default admin creation failed: {exc}')
