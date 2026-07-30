from app import create_app

app = create_app()
# Table creation, auto-migration, academic-structure seeding, and the first
# admin account are all handled inside create_app() -> app/bootstrap.py, so
# they run no matter how the app is started (this file's __main__ block,
# `flask run`, or gunicorn on Render). See app/bootstrap.py for details.

if __name__ == '__main__':
    print('\n' + '=' * 60)
    print(f"🎓 {app.config['APP_NAME']} — running at http://localhost:5000")
    print('=' * 60)
    app.run(host='0.0.0.0', port=5000, debug=app.config.get('DEBUG', False))
