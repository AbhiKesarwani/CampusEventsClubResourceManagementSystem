# routes/search.py
from flask import Blueprint, render_template, request, session, jsonify, url_for
from helpers.auth_helpers import login_required
from services.user_service import get_user_by_id
from services.certificate_service import search_certificates
from services.connect_service import (
    search_contacts, get_announcements_for_user, get_inbox, get_ai_history
)
from database import get_db_connection
import math

bp = Blueprint('search', __name__, url_prefix='/search')

PER_PAGE = 12


# ── Shared query helpers (reused by both the full results page and the
#    Ctrl+K quick-search palette — never duplicate this SQL) ──────────────

def _search_events(like: str, limit: int = 20, offset: int = 0) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
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
        """, (like, like, like, limit, offset))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def _count_events(like: str) -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM events e
            WHERE e.title LIKE %s OR e.description LIKE %s OR e.event_lead LIKE %s
        """, (like, like, like))
        return (cur.fetchone() or {}).get('cnt', 0)
    finally:
        if cur: cur.close()
        if conn: conn.close()


def _search_clubs(like: str, limit: int = 20) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT c.club_id, c.club_name, c.description,
                   u.name AS coordinator_name,
                   (SELECT img_path FROM club_images WHERE club_id=c.club_id LIMIT 1) AS first_image
            FROM clubs c
            LEFT JOIN users u ON c.coordinator_id = u.user_id
            WHERE c.club_name LIKE %s OR c.description LIKE %s OR u.name LIKE %s
            LIMIT %s
        """, (like, like, like, limit))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def _search_venues(like: str, limit: int = 20) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT venue_id, venue_name, capacity, location
            FROM venues
            WHERE venue_name LIKE %s OR location LIKE %s
            LIMIT %s
        """, (like, like, limit))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def _search_resources(like: str, limit: int = 20) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT resource_id, resource_name, total_quantity, description
            FROM resources
            WHERE resource_name LIKE %s OR description LIKE %s
            LIMIT %s
        """, (like, like, limit))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def _search_coordinators(like: str, limit: int = 20) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT u.user_id, u.name, u.email, u.role,
                   c.club_id, c.club_name,
                   (SELECT img_path FROM club_images WHERE club_id=c.club_id LIMIT 1) AS club_image
            FROM users u
            LEFT JOIN clubs c ON c.coordinator_id = u.user_id
            WHERE u.role IN ('club_admin', 'admin')
              AND (u.name LIKE %s OR u.email LIKE %s OR c.club_name LIKE %s)
            LIMIT %s
        """, (like, like, like, limit))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


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
        events_total = _count_events(like)
        events       = _search_events(like, limit=PER_PAGE, offset=offset)
        clubs        = _search_clubs(like, limit=20)
        venues       = _search_venues(like, limit=20)
        resources    = _search_resources(like, limit=20)
        coordinators = _search_coordinators(like, limit=10)

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


# ── Ctrl+K global quick-search (JSON) ───────────────────────────────────────

@bp.route('/api/quick')
@login_required
def quick():
    """
    Campus-wide quick search for the Ctrl+K command palette. Returns a flat,
    capped list of results across every searchable area, respecting the same
    RBAC each area already enforces on its own pages/services (never a
    broader view than the user would otherwise have).
    """
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({'items': []})

    user_id = session['user_id']
    role    = session.get('role', 'student')
    club_id = session.get('club_id')
    like    = f"%{q}%"
    items   = []

    for e in _search_events(like, limit=5):
        items.append({
            'category': 'Events', 'icon': 'calendar-days', 'title': e['title'],
            'subtitle': f"{e.get('club_name') or ''} · {e['date'] or 'TBD'}",
            'url': url_for('events.detail', event_id=e['event_id']),
        })

    for c in _search_clubs(like, limit=5):
        items.append({
            'category': 'Clubs', 'icon': 'users', 'title': c['club_name'],
            'subtitle': c.get('coordinator_name') and f"Coordinator: {c['coordinator_name']}" or 'No coordinator assigned',
            'url': url_for('clubs.detail', club_id=c['club_id']),
        })

    for v in _search_venues(like, limit=5):
        items.append({
            'category': 'Venues', 'icon': 'building-2', 'title': v['venue_name'],
            'subtitle': v.get('location') or '',
            'url': url_for('venues.detail', venue_id=v['venue_id']),
        })

    for r in _search_resources(like, limit=5):
        items.append({
            'category': 'Resources', 'icon': 'package', 'title': r['resource_name'],
            'subtitle': f"{r['total_quantity']} in stock",
            'url': url_for('resources.list_resources'),
        })

    # People: reuses Campus Connect's own RBAC-scoped contact search, so a
    # student only ever sees coordinators, a coordinator only their own club,
    # and an admin sees everyone — identical rules as starting a new chat.
    for p in search_contacts(q, user_id, role, club_id)[:5]:
        items.append({
            'category': 'People', 'icon': 'user', 'title': p['name'],
            'subtitle': (p.get('club_name') and f"Coordinator · {p['club_name']}") or p.get('role', '').replace('_', ' ').title(),
            'url': f"{url_for('connect.index')}?tab=messages&with={p['user_id']}",
        })

    for cert in search_certificates(q, user_id, role, limit=5):
        items.append({
            'category': 'Certificates', 'icon': 'award', 'title': cert['event_title'],
            'subtitle': f"{cert['student_name']} · {cert['issue_date'] or ''}" if role == 'admin' else (cert['issue_date'] or ''),
            'url': url_for('certificates.my_certificates'),
        })

    for ann in get_announcements_for_user(user_id, role, club_id, page=1, per_page=100):
        if q.lower() in (ann['title'] + ' ' + ann['body']).lower():
            items.append({
                'category': 'Announcements', 'icon': 'megaphone', 'title': ann['title'],
                'subtitle': f"By {ann['author_name']}",
                'url': f"{url_for('connect.index')}?tab=announcements&ann={ann['ann_id']}",
            })
            if len([i for i in items if i['category'] == 'Announcements']) >= 5:
                break

    for conv in get_inbox(user_id):
        if q.lower() in (conv['name'] or '').lower():
            items.append({
                'category': 'Campus Connect', 'icon': 'message-square', 'title': conv['name'],
                'subtitle': (conv.get('last_body') or '')[:60],
                'url': f"{url_for('connect.index')}?tab=messages&with={conv['other_id']}",
            })
            if len([i for i in items if i['category'] == 'Campus Connect']) >= 5:
                break

    for turn in get_ai_history(user_id, limit=100):
        if turn['role'] == 'user' and q.lower() in turn['content'].lower():
            items.append({
                'category': 'AI History', 'icon': 'bot', 'title': turn['content'][:80],
                'subtitle': 'Ask Campus Connect Assistant',
                'url': f"{url_for('connect.index')}?tab=ai",
            })
            if len([i for i in items if i['category'] == 'AI History']) >= 3:
                break

    if role in ('admin', 'club_admin'):
        for coord in _search_coordinators(like, limit=5):
            items.append({
                'category': 'Coordinators', 'icon': 'user-cog', 'title': coord['name'],
                'subtitle': coord.get('club_name') or coord['email'],
                'url': url_for('admin.coordinators') if role == 'admin' else url_for('clubs.list_clubs'),
            })

    return jsonify({'items': items[:40]})
