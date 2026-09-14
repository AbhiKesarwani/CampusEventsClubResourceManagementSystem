# wsgi.py — Production WSGI entry point for CampusOps
# ─────────────────────────────────────────────────────────────────────────────
# Development:   python app.py
# Production:    python wsgi.py
#                OR: waitress-serve --call wsgi:application
# ─────────────────────────────────────────────────────────────────────────────
import os
import logging
from app import create_app
from config import Config

logger = logging.getLogger(__name__)

# Create the WSGI application object that Waitress (or any PEP-3333 server)
# will call for every incoming request.
application = create_app()


if __name__ == '__main__':
    # Direct invocation:  python wsgi.py
    # Starts Waitress with configurable threads — defaults to 8, which gives
    # solid concurrency on a single server without exhausting DB pool.
    import waitress

    host    = os.getenv('HOST', '0.0.0.0')
    port    = int(os.getenv('PORT', '5000'))
    threads = Config.WAITRESS_THREADS

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )
    logger.info(
        "Starting CampusOps via Waitress on %s:%s (%d threads, DB pool=%s)",
        host, port, threads, Config.DB_POOL_SIZE,
    )
    waitress.serve(application, host=host, port=port, threads=threads)
