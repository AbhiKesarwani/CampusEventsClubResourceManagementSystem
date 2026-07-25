# routes/search.py
from flask import Blueprint, render_template, request, session
from helpers.auth_helpers import login_required
from services.user_service import get_user_by_id
from database import get_db_connection
import math

bp = Blueprint('search', __name__, url_prefix='/search')

PER_PAGE = 12


@bp.route('/')
@login_required
def results():
    q    = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    user = get_user_by_id(session['user_id'])

    events, clubs, venues, resources, coordinators = [], [], [], [], []
    events_total = 0

    if q:
        like   = f"%{q}%"
        offset = (page - 1) * PER_PAGE
        conn = cur = None
        try:
            conn = get_db_connection()
            cur  = conn.cursor(dictionary=True)

            # Events count (for pagination)
            cur.execute("""
                SELECT COUNT(*) AS cnt FROM events e
                WHERE e.title LIKE %s OR e.description LIKE %s OR e.event_lead LIKE %s
            """, (like, like, like))
            events_total = (cur.fetchone() or {}).get('cnt', 0)

            # Events (paginated)
            cur.execute("""
                SELECT e.event_id, e.title, e.date, e.start_time, e.end_time,
                       c.club_name, v.venue_name,
                       (SELECT img_path FROM event_images WHERE event_id=e.event_id LIMIT 1) AS first_image
                FROM events e
                LEFT JOIN clubs  c ON e.club_id  = c.club_id
                LEFT JOIN venues v ON e.venue_id = v.venue_id
                WHERE e.title LIKE %s OR e.description LIKE %s OR e.event_lead LIKE %s
                ORDER BY e.date DESC
                LIMIT %s OFFSET %s
            """, (like, like, like, PER_PAGE, offset))
            events = cur.fetchall()

            # Clubs
            cur.execute("""
                SELECT c.club_id, c.club_name, c.description,
                       u.name AS coordinator_name,
                       (SELECT img_path FROM club_images WHERE club_id=c.club_id LIMIT 1) AS first_image
                FROM clubs c
                LEFT JOIN users u ON c.coordinator_id = u.user_id
                WHERE c.club_name LIKE %s OR c.description LIKE %s OR u.name LIKE %s
                LIMIT 20
            """, (like, like, like))
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

            # Coordinators
            cur.execute("""
                SELECT u.user_id, u.name, u.email, u.role,
                       c.club_id, c.club_name,
                       (SELECT img_path FROM club_images WHERE club_id=c.club_id LIMIT 1) AS club_image
                FROM users u
                LEFT JOIN clubs c ON c.coordinator_id = u.user_id
                WHERE u.role IN ('club_admin', 'admin')
                  AND (u.name LIKE %s OR u.email LIKE %s OR c.club_name LIKE %s)
                LIMIT 10
            """, (like, like, like))
            coordinators = cur.fetchall()

        finally:
            if cur: cur.close()
            if conn: conn.close()

    total_pages = max(1, math.ceil(events_total / PER_PAGE)) if q else 1
    page        = max(1, min(page, total_pages))
    total       = events_total + len(clubs) + len(venues) + len(resources) + len(coordinators)

    return render_template('search_results.html',
                           q=q, total=total,
                           events=events, clubs=clubs,
                           venues=venues, resources=resources,
                           coordinators=coordinators,
                           events_total=events_total,
                           page=page, total_pages=total_pages,
                           user=user, active=None)
