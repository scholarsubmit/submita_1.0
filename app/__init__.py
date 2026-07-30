"""
app/__init__.py — application factory. This is the ONE place everything
gets wired together, which is what makes the blueprint separation of
concern actually work (auth/admin/student/lecturer routes never import
Flask app instances directly, only the shared `db`/`login_manager` from
extensions.py).
"""
import os
from datetime import datetime

from flask import Flask, render_template
from flask_wtf.csrf import CSRFError

from config import CONFIG_MAP
from app.extensions import db, login_manager, csrf, limiter


def create_app(config_name=None):
    config_name = config_name or os.environ.get('FLASK_ENV')
    if not config_name:
        # Render sets RENDER=true on every service automatically. If FLASK_ENV
        # was never configured in the dashboard, fail safe to production
        # settings there instead of silently running with DEBUG=True (which
        # would show visitors interactive stack traces and leak secrets).
        config_name = 'production' if os.environ.get('RENDER') else 'default'
    app = Flask(__name__, static_folder='../static', template_folder='../templates')
    app.config.from_object(CONFIG_MAP.get(config_name, CONFIG_MAP['default']))

    # ── Extensions ────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # ── Database bootstrap: tables, seed data, first admin ─────────
    # Must happen here (not in run.py's __main__ block) since gunicorn
    # imports this factory directly and never runs that block.
    from app.bootstrap import bootstrap_database
    bootstrap_database(app, db)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ── Blueprints ────────────────────────────────────────────────
    from app.blueprints.auth import auth_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.api import api_bp
    from app.blueprints.assignments import assignments_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(assignments_bp)

    # ── Security headers on every response ───────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        if app.config.get('SESSION_COOKIE_SECURE'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # ── Global template context ───────────────────────────────────
    @app.context_processor
    def inject_globals():
        return {'now': datetime.utcnow(), 'app_name': app.config['APP_NAME']}

    # ── Error handlers ────────────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(429)
    def rate_limited(e):
        return render_template('errors/429.html'), 429

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(Exception)
    def unhandled_exception(e):
        # Safety net: catches anything that isn't a plain HTTPException
        # (e.g. a raw SQLAlchemy/OperationalError) so a visitor always sees
        # the styled 500 page instead of a bare "Internal Server Error"
        # or, worse, a raw traceback if DEBUG ever ends up on in production.
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            raise e
        db.session.rollback()
        app.logger.exception('Unhandled exception')
        return render_template('errors/500.html'), 500

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        return render_template('errors/403.html', reason='Your session expired. Please try again.'), 400

    # ── PWA: manifest + service worker need to be served from root ──
    @app.route('/manifest.json')
    def manifest():
        return app.send_static_file('manifest.json')

    @app.route('/robots.txt')
    def robots():
        return app.send_static_file('robots.txt')

    @app.route('/sw.js')
    def service_worker():
        # Service workers must be served from the root scope, not /static/,
        # or their caching scope is limited to the /static/ path.
        response = app.send_static_file('sw.js')
        response.headers['Service-Worker-Allowed'] = '/'
        return response

    @app.route('/')
    def landing():
        return render_template('shared/landing.html')

    @app.route('/offline')
    def offline():
        return render_template('shared/offline.html')

    return app
