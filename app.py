# app.py — Flask application factory
import os
import logging
from flask import Flask, render_template, session
from flask_wtf import CSRFProtect

from config import Config
from services.user_service import get_user_by_id

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config_class)
    app.secret_key = config_class.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = config_class.MAX_UPLOAD_BYTES

    # CSRF protection for every state-changing request (forms + AJAX).
    # Forms get an auto-injected hidden csrf_token via JS in layout.html;
    # fetch()/AJAX calls get it via the X-CSRFToken header (also injected
    # globally in layout.html) — see templates/layout.html.
    CSRFProtect(app)

    # Ensure required folders exist
    for folder in [config_class.UPLOAD_FOLDER, config_class.CERT_FOLDER]:
        os.makedirs(folder, exist_ok=True)

    # ── Register Blueprints ───────────────────────────────────────────────────
    from routes.auth            import bp as auth_bp
    from routes.dashboard       import bp as dashboard_bp
    from routes.clubs           import bp as clubs_bp
    from routes.events          import bp as events_bp
    from routes.venues          import bp as venues_bp
    from routes.recommendations import bp as recs_bp
    from routes.attendance      import bp as attendance_bp
    from routes.certificates    import bp as certs_bp
    from routes.search          import bp as search_bp
    from routes.notifications   import bp as notifs_bp
    from routes.admin           import bp as admin_bp
    from routes.connect         import bp as connect_bp
    from routes.profile         import bp as profile_bp
    from routes.settings        import bp as settings_bp
    from routes.calendar        import bp as calendar_bp
    from routes.export          import bp as export_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clubs_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(venues_bp)
    app.register_blueprint(recs_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(certs_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(notifs_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(connect_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(export_bp)

    # ── Jinja Globals ─────────────────────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        from datetime import date as _date
        user = None
        unread_count = 0
        cc_unread_count = 0
        if 'user_id' in session:
            try:
                from services.notification_service import count_unread
                from services.connect_service import count_unread_messages
                user = get_user_by_id(session['user_id'])
                unread_count = count_unread(session['user_id'])
                cc_unread_count = count_unread_messages(session['user_id'])
            except Exception:
                pass
        return dict(current_user=user, session=session, unread_count=unread_count,
                   cc_unread_count=cc_unread_count,
                   today_str=_date.today().strftime('%Y-%m-%d'))

    # ── Jinja Filters ─────────────────────────────────────────────────────────
    from datetime import datetime as _dt

    @app.template_filter('timeago')
    def timeago_filter(dt):
        """Convert a datetime to a human-friendly relative time string."""
        if not dt:
            return ''
        if hasattr(dt, 'replace'):
            now = _dt.now()
            diff = now - dt.replace(tzinfo=None)
            seconds = int(diff.total_seconds())
        else:
            return str(dt)

        if seconds < 60:
            return 'just now'
        elif seconds < 3600:
            m = seconds // 60
            return f"{m} minute{'s' if m != 1 else ''} ago"
        elif seconds < 86400:
            h = seconds // 3600
            return f"{h} hour{'s' if h != 1 else ''} ago"
        elif seconds < 604800:
            d = seconds // 86400
            return f"{d} day{'s' if d != 1 else ''} ago"
        elif seconds < 2592000:
            w = seconds // 604800
            return f"{w} week{'s' if w != 1 else ''} ago"
        else:
            return dt.strftime('%d %b %Y')

    @app.template_filter('datetimeformat')
    def datetimeformat_filter(dt, fmt='%d %b %Y'):
        if not dt:
            return ''
        if hasattr(dt, 'strftime'):
            return dt.strftime(fmt)
        return str(dt)


    # ── Error Handlers ────────────────────────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        user = get_user_by_id(session['user_id']) if 'user_id' in session else None
        return render_template('403.html', user=user), 403

    @app.errorhandler(404)
    def not_found(e):
        user = get_user_by_id(session['user_id']) if 'user_id' in session else None
        return render_template('404.html', user=user), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("500 error: %s", e)
        user = get_user_by_id(session['user_id']) if 'user_id' in session else None
        return render_template('500.html', user=user), 500

    @app.errorhandler(413)
    def too_large(e):
        from flask import flash, redirect, request as req
        flash("File too large (max 5 MB).", "danger")
        return redirect(req.referrer or '/')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=Config.DEBUG)
