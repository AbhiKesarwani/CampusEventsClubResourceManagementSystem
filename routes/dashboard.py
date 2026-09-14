# routes/dashboard.py
import json
from datetime import datetime
from flask import Blueprint, render_template, session
from helpers.auth_helpers import login_required
from services.user_service import get_user_by_id
from services.event_service import get_upcoming_events, count_events, get_events_for_club
from services.club_service import get_all_clubs, get_club_by_id
from services.venue_service import count_venues
from services.attendance_service import (
    count_attendance, get_user_attendance,
    get_top_events_by_attendance, get_top_clubs_by_attendance,
    get_top_students_by_attendance, get_club_monthly_attendance,
    get_most_attended_event
)
from services.certificate_service import get_user_certificates
from services.recommendation_service import get_recommendations
from services.log_service import get_recent_activity
from services.member_service import get_member_count

bp = Blueprint('dashboard', __name__)


def _get_greeting() -> str:
    """Return time-appropriate greeting based on server hour."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 17:
        return "Good Afternoon"
    elif 17 <= hour < 21:
        return "Good Evening"
    else:
        return "Good Night"


@bp.route('/')
@login_required
def index():
    user = get_user_by_id(session['user_id'])
    role = session.get('role')

    ctx = dict(user=user, active='dashboard', role=role, greeting=_get_greeting())

    upcoming = get_upcoming_events(limit=6)
    ctx['upcoming_events'] = upcoming
    if role == 'admin':
        ctx.update(_admin_stats())
        ctx['recommended_events'] = []  # Admin never gets recommendations

    elif role == 'club_admin':
        club_id = session.get('club_id')
        ctx.update(_club_admin_stats(club_id))
        ctx['recommended_events'] = []  # Coordinator never gets recommendations

    else:  # student
        ctx.update(_student_stats(session['user_id']))
        try:
            ctx['recommended_events'] = get_recommendations(session['user_id'], limit=3)
        except Exception:
            ctx['recommended_events'] = []

    return render_template('dashboard.html', **ctx)


# ── Per-role stat helpers ──────────────────────────────────────────────────────

def _admin_stats() -> dict:
    clubs      = get_all_clubs()
    recent_act = get_recent_activity(10)

    # Analytics for charts
    top_events   = get_top_events_by_attendance(5)
    top_clubs    = get_top_clubs_by_attendance(5)
    top_students = get_top_students_by_attendance(5)
    top_event    = get_most_attended_event()

    return {
        'stat_events':          count_events(),
        'stat_clubs':           len(clubs),
        'stat_venues':          count_venues(),
        'stat_attendance':      count_attendance(),
        'recent_activity':      recent_act,
        'top_event':            top_event,
        # Chart.js JSON
        'chart_events_labels':  json.dumps([e['title'][:20] for e in top_events]),
        'chart_events_data':    json.dumps([e['count'] for e in top_events]),
        'chart_clubs_labels':   json.dumps([c['club_name'][:20] for c in top_clubs]),
        'chart_clubs_data':     json.dumps([c['count'] for c in top_clubs]),
        'chart_students_labels': json.dumps([s['name'][:20] for s in top_students]),
        'chart_students_data':  json.dumps([s['count'] for s in top_students]),
    }


def _club_admin_stats(club_id) -> dict:
    if not club_id:
        return {
            'my_club': None, 'my_events': [],
            'stat_events': 0, 'stat_members': 0,
            'stat_pending_requests': 0, 'pending_requests': [],
            'stat_attendance': 0,
            'chart_monthly_labels': json.dumps([]),
            'chart_monthly_data':   json.dumps([]),
        }
    my_club     = get_club_by_id(club_id)
    my_events   = get_events_for_club(club_id)
    member_cnt  = get_member_count(club_id)

    monthly = get_club_monthly_attendance(club_id, 6)

    from services.membership_service import get_requests_for_club
    all_pending = get_requests_for_club(club_id, status='Pending')
    pending_cnt = len(all_pending)

    return {
        'my_club':      my_club,
        'my_events':    my_events,
        'stat_events':  len(my_events),
        'stat_members': member_cnt,
        'stat_pending_requests': pending_cnt,
        'pending_requests': all_pending[:10],
        'stat_attendance': count_attendance(),
        'chart_monthly_labels': json.dumps([m['month'] for m in monthly]),
        'chart_monthly_data':   json.dumps([m['count'] for m in monthly]),
    }


def _student_stats(user_id) -> dict:
    attended = get_user_attendance(user_id)
    certs    = get_user_certificates(user_id)
    return {
        'stat_attended':      len(attended),
        'stat_certificates':  len(certs),
        'attendance_history': attended[:5],
        'certificates':       certs[:5],
    }
