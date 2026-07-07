# routes/search.py
from flask import Blueprint, render_template, request, session
from helpers.auth_helpers import login_required
from services.user_service import get_user_by_id
from database import get_db_connection

bp = Blueprint('search', __name__, url_prefix='/search')


@bp.route('/')
@login_required
def results():
    q    = request.args.get('q', '').strip()
    user = get_user_by_id(session['user_id'])

    events, clubs, venues, resources = [], [], [], []

    if q:
        like = f"%{q}%"
        conn = cur = None
        try:
            conn = get_db_connection()
            cur  = conn.cursor(dictionary=True)

            # Events
            cur.execute("""
                SELECT e.event_id, e.title, e.date, c.club_name, v.venue_name,
                       (SELECT img_path FROM event_images WHERE event_id=e.event_id LIMIT 1) AS first_image
                FROM events e
                LEFT JOIN clubs  c ON e.club_id  = c.club_id
                LEFT JOIN venues v ON e.venue_id = v.venue_id
                WHERE e.title LIKE %s OR e.description LIKE %s
                ORDER BY e.date DESC LIMIT 20
            """, (like, like))
            events = cur.fetchall()

            # Clubs
            cur.execute("""
                SELECT c.club_id, c.club_name, c.description,
                       u.name AS coordinator_name,
                       (SELECT img_path FROM club_images WHERE club_id=c.club_id LIMIT 1) AS first_image
                FROM clubs c
                LEFT JOIN users u ON c.coordinator_id = u.user_id
                WHERE c.club_name LIKE %s OR c.description LIKE %s
                LIMIT 20
            """, (like, like))
            clubs = cur.fetchall()

            # Venues
            cur.execute("""
                SELECT venue_id, venue_name, capacity, location
                FROM venues
                WHERE venue_name LIKE %s OR location LIKE %s
                LIMIT 20
            """, (like, like))
            venues = cur.fetchall()

            # Resources
            cur.execute("""
                SELECT resource_id, resource_name, total_quantity, description
                FROM resources
                WHERE resource_name LIKE %s OR description LIKE %s
                LIMIT 20
            """, (like, like))
            resources = cur.fetchall()

        finally:
            if cur: cur.close()
            if conn: conn.close()

    total = len(events) + len(clubs) + len(venues) + len(resources)

    return render_template('search_results.html',
                           q=q, total=total,
                           events=events, clubs=clubs,
                           venues=venues, resources=resources,
                           user=user, active=None)
