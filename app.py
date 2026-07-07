# app.py — Flask application factory
import os
import logging
from flask import Flask, render_template, session

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
    app.secret_key       = config_class.SECRET_KEY
    app.config['UPLOAD_FOLDER'] = config_class.UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = config_class.MAX_UPLOAD_BYTES

    # Ensure required folders exist
    for folder in [config_class.UPLOAD_FOLDER, config_class.QR_FOLDER, config_class.CERT_FOLDER]:
        os.makedirs(folder, exist_ok=True)

    # ── Register Blueprints ───────────────────────────────────────────────────
    from routes.auth            import bp as auth_bp
    from routes.dashboard       import bp as dashboard_bp
    from routes.clubs           import bp as clubs_bp
    from routes.events          import bp as events_bp
    from routes.venues          import bp as venues_bp
    from routes.resources       import bp as resources_bp
    from routes.recommendations import bp as recs_bp
    from routes.attendance      import bp as attendance_bp
    from routes.certificates    import bp as certs_bp
    from routes.search          import bp as search_bp
    from routes.notifications   import bp as notifs_bp
    from routes.admin           import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clubs_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(venues_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(recs_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(certs_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(notifs_bp)
    app.register_blueprint(admin_bp)

    # ── Jinja Globals ─────────────────────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        user = None
        unread_count = 0
        if 'user_id' in session:
            try:
                from services.notification_service import count_unread
                user = get_user_by_id(session['user_id'])
                unread_count = count_unread(session['user_id'])
            except Exception:
                pass
        return dict(current_user=user, session=session, unread_count=unread_count)

    # ── Error Handlers ────────────────────────────────────────────────────────
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
