from app import create_app
from app.extensions import db

app = create_app()


def _auto_migrate():
    """
    Adds any columns that exist in models.py but are missing from an
    already-created database — safe to run every startup, only acts on
    what's actually missing. Means adding a field to a model later
    doesn't force everyone to delete their database and start over.
    """
    from sqlalchemy import text, inspect as sa_inspect
    inspector = sa_inspect(db.engine)

    def add_if_missing(table, column, col_def):
        try:
            existing = {c['name'] for c in inspector.get_columns(table)}
            if column not in existing:
                with db.engine.connect() as conn:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col_def}'))
                    conn.commit()
                print(f'  ✅ Migrated: {table}.{column}')
        except Exception as exc:
            print(f'  ⚠️  Could not add {table}.{column}: {exc}')

    add_if_missing('assignments', 'semester', "semester VARCHAR(10) NOT NULL DEFAULT 'First'")
    add_if_missing('assignments', 'academic_year', "academic_year VARCHAR(20) NOT NULL DEFAULT '2025/2026'")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        _auto_migrate()
        print('✅ Database tables created/verified.')
    print('\n' + '=' * 60)
    print(f"🎓 {app.config['APP_NAME']} — running at http://localhost:5000")
    print('=' * 60)
    app.run(host='0.0.0.0', port=5000, debug=app.config.get('DEBUG', False))
