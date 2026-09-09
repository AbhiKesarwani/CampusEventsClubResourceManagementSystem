# routes/calendar.py
"""Calendar view (month / agenda) for events — reuses event_service and
attendance_service, no duplicate queries."""
from flask import Blueprint, render_template, request, jsonify, session, url_for
from datetime import date
import calendar as _calendar_mod
from helpers.auth_helpers import login_required
from services.user_service import get_user_by_id
from services.event_service import get_all_events

bp = Blueprint('calendar', __name__, url_prefix='/calendar')


@bp.route('/')
@login_required
def index():
    today = date.today()
    year  = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)
    view  = request.args.get('view', 'month')  # 'month' | 'agenda'

    # Clamp to valid month range
    month = max(1, min(12, month))

    first_day = date(year, month, 1)
    last_day  = date(year, month, _calendar_mod.monthrange(year, month)[1])

    events = get_all_events(date_from=first_day.isoformat(), date_to=last_day.isoformat())

    events_by_day: dict[int, list] = {}
    for e in events:
        if e.get('date'):
            events_by_day.setdefault(e['date'].day, []).append(e)

    cal = _calendar_mod.Calendar(firstweekday=0)  # Monday-first
    weeks = cal.monthdayscalendar(year, month)

    prev_month = (month - 1) or 12
    prev_year  = year if month > 1 else year - 1
    next_month = (month % 12) + 1
    next_year  = year if month < 12 else year + 1

    user = get_user_by_id(session['user_id'])
    role = session.get('role')

    return render_template(
        'calendar.html',
        user=user, active='calendar', role=role,
        year=year, month=month, view=view,
        month_name=_calendar_mod.month_name[month],
        weeks=weeks, events_by_day=events_by_day,
        today=today,
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month,
        agenda_events=sorted(events, key=lambda e: (e['date'] or today, e['start_time'] or '')),
    )


@bp.route('/api/day')
@login_required
def day_detail():
    """Return events for a specific day with venue/time/coordinator/attendance
    status — used by the "click a day" popover."""
    date_str = request.args.get('date', '')
    try:
        y, m, d = (int(x) for x in date_str.split('-'))
        target = date(y, m, d)
    except (ValueError, AttributeError):
        return jsonify({'error': 'Invalid date'}), 400

    from services.attendance_service import has_attended
    from services.club_service import get_club_by_id
    events = get_all_events(date_from=target.isoformat(), date_to=target.isoformat())

    items = []
    for e in events:
        club = get_club_by_id(e['club_id']) if e.get('club_id') else None
        items.append({
            'event_id': e['event_id'],
            'title': e['title'],
            'club_name': e.get('club_name'),
            'coordinator_name': club.get('coordinator_name') if club else None,
            'venue_name': e.get('venue_name'),
            'start_time': str(e['start_time']) if e.get('start_time') else None,
            'end_time': str(e['end_time']) if e.get('end_time') else None,
            'approved_status': e.get('approved_status'),
            'attended': has_attended(e['event_id'], session['user_id']),
            'url': url_for('events.detail', event_id=e['event_id']),
        })
    return jsonify({'date': target.isoformat(), 'events': items})
