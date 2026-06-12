"""
migrate_db.py — Run this ONCE to bring your SQLite database schema up to date.

Usage:
    python migrate_db.py

Place this file in the same folder as your app.py, then run it.
It is safe to run multiple times — it checks before adding each column.
"""

import sqlite3
import os
import sys
from datetime import datetime

# ── Locate the database file ──────────────────────────────────────────────────
# Flask stores SQLite files in the 'instance' folder next to app.py
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_CANDIDATES = [
    os.path.join(SCRIPT_DIR, 'instance', 'submita.db'),
    os.path.join(SCRIPT_DIR, 'submita.db'),
]

DB_PATH = None
for candidate in DB_CANDIDATES:
    if os.path.exists(candidate):
        DB_PATH = candidate
        break

if not DB_PATH:
    print("❌  Could not find submita.db")
    print("    Looked in:")
    for c in DB_CANDIDATES:
        print(f"      {c}")
    sys.exit(1)

print(f"✅  Found database: {DB_PATH}")

# ── Helper ────────────────────────────────────────────────────────────────────
def get_existing_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}   # set of column names


def add_column_if_missing(cursor, table, column, col_type, default=None):
    existing = get_existing_columns(cursor, table)
    if column in existing:
        print(f"   ✓  {table}.{column} already exists — skipped")
        return False
    if default is not None:
        sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}"
    else:
        sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
    cursor.execute(sql)
    print(f"   ➕  Added {table}.{column} ({col_type})")
    return True


# ── Migrations ────────────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n── assignments table ────────────────────────────────────────")

# Columns the model defines that were missing from the DB
migrations = [
    # (column_name,            sql_type,                  default_value)
    ("target_level",           "VARCHAR(10)  NOT NULL",   "'100'"),
    ("target_department_id",   "INTEGER",                 None),
    ("target_semester",        "VARCHAR(20)  NOT NULL",   "'First'"),
    ("target_academic_year",   "VARCHAR(20)  NOT NULL",   f"'{datetime.now().year}/{datetime.now().year + 1}'"),
    ("target_course_id",       "INTEGER",                 None),
    ("is_published",           "BOOLEAN      NOT NULL",   "0"),
    ("published_at",           "DATETIME",                None),
    ("is_locked",              "BOOLEAN      NOT NULL",   "0"),
    ("late_submission_penalty","FLOAT        NOT NULL",   "10.0"),
    ("max_file_size",          "INTEGER      NOT NULL",   "10"),
    ("allowed_file_types",     "VARCHAR(200)",            None),
    ("plagiarism_threshold",   "FLOAT        NOT NULL",   "30.0"),
    ("attachment_path",        "VARCHAR(500)",            None),
    ("attachment_filename",    "VARCHAR(200)",            None),
    ("attachment_type",        "VARCHAR(50)",             None),
    ("course_id",              "INTEGER",                 None),
    ("questions",              "TEXT",                    None),
    ("instructions",           "TEXT",                    None),
    ("total_points",           "INTEGER      NOT NULL",   "100"),
]

changed = 0
for col, col_type, default in migrations:
    if add_column_if_missing(cursor, "assignments", col, col_type, default):
        changed += 1

# ── Add foreign key indexes SQLite doesn't enforce but speeds up JOINs ───────
print("\n── indexes ──────────────────────────────────────────────────")
indexes = [
    ("idx_assignments_target_level",         "assignments(target_level)"),
    ("idx_assignments_target_department",    "assignments(target_department_id)"),
    ("idx_assignments_target_semester",      "assignments(target_semester)"),
    ("idx_assignments_target_academic_year", "assignments(target_academic_year)"),
    ("idx_assignments_is_published",         "assignments(is_published)"),
    ("idx_assignments_deadline",             "assignments(deadline)"),
]

for idx_name, idx_def in indexes:
    try:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
        print(f"   ✓  Index {idx_name}")
    except sqlite3.OperationalError as e:
        print(f"   ⚠  Index {idx_name}: {e}")

conn.commit()
conn.close()

print(f"\n{'─'*55}")
if changed:
    print(f"✅  Migration complete — {changed} column(s) added.")
else:
    print("✅  Database was already up to date — nothing changed.")

print("   You can now restart your Flask app.\n")