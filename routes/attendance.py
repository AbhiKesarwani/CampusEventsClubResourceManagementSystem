# routes/attendance.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from helpers.auth_helpers import login_required
from services.user_service import get_user_by_id
from services.event_service import get_event_by_id
from services.attendance_service import (
    generate_attendance_code, get_event_by_attendance_code,
    mark_attendance_by_code, mark_attendance,
    get_attendance_for_event, has_attended,
    submit_code_self, get_upcoming_events_for_user,
    get_student_attendance_history, expire_attendance_code
)

bp = Blueprint('attendance', __name__, url_prefix='/attendance')


# ──────────────────────────────────────────────────────────────
#  STUDENT ROUTES
# ──────────────────────────────────────────────────────────────

@bp.route('/my')
@login_required
def my_attendance():
    """
    Student: view events with active codes + submit code + attendance history.
    """
    user_id = session['user_id']
    user    = get_user_by_id(user_id)

    active_events = get_upcoming_events_for_user(user_id)
    history       = get_student_attendance_history(user_id)

    return render_template('attendance/my.html',
                           active_events=active_events,
                           history=history,
                           user=user,
                           active='attendance')


@bp.route('/submit', methods=['POST'])
@login_required
def submit_code():
    """
    Student self-submits an attendance code (AJAX or form POST).
    """
    user_id  = session['user_id']
    is_ajax  = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json

    if is_ajax:
        data = request.get_json(force=True) or {}
        code = data.get('code', '').strip().upper()
        if not code:
            return jsonify({'success': False, 'message': 'Attendance code is required.'})
        result = submit_code_self(code, user_id)
        return jsonify(result)

    # Regular form POST fallback
    code = request.form.get('code', '').strip().upper()
    if not code:
        flash('Please enter an attendance code.', 'danger')
        return redirect(url_for('attendance.my_attendance'))

    result = submit_code_self(code, user_id)
    flash(result['message'], 'success' if result['success'] else 'danger')
    return redirect(url_for('attendance.my_attendance'))



# ──────────────────────────────────────────────────────────────
#  COORDINATOR / ADMIN ROUTES
# ──────────────────────────────────────────────────────────────

@bp.route('/code/<int:event_id>')
@login_required
def show_code(event_id):
    """Admin or Club Coordinator views/generates attendance code for an event."""
    role = session.get('role')
    if role not in ('admin', 'club_admin'):
        flash("Only admins/club coordinators can manage attendance codes.", "danger")
        return redirect(url_for('events.detail', event_id=event_id))

    event = get_event_by_id(event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('events.list_events'))

    # If no code exists yet, generate one automatically
    if not event.get('attendance_code'):
        try:
            code = generate_attendance_code(event_id)
            event['attendance_code'] = code
            flash("Attendance code generated!", "success")
        except Exception as e:
            flash(f"Could not generate code: {e}", "danger")

    records = get_attendance_for_event(event_id)
    user    = get_user_by_id(session['user_id'])

    # Check expiry status
    from datetime import datetime
    code_active = True
    if event.get('code_expires_at'):
        exp = event['code_expires_at']
        if isinstance(exp, str):
            try:
                exp = datetime.fromisoformat(exp)
            except ValueError:
                exp = None
        if exp and exp < datetime.now():
            code_active = False

    return render_template('attendance/code.html',
                           event=event,
                           attendance_records=records,
                           user=user,
                           code_active=code_active,
                           active='events')


@bp.route('/code/<int:event_id>/regenerate', methods=['POST'])
@login_required
def regenerate_code(event_id):
    """Regenerate the attendance code for an event."""
    role = session.get('role')
    if role not in ('admin', 'club_admin'):
        flash("Permission denied.", "danger")
        return redirect(url_for('events.detail', event_id=event_id))
    try:
        generate_attendance_code(event_id)
        flash("Attendance code regenerated.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for('attendance.show_code', event_id=event_id))


@bp.route('/code/<int:event_id>/expire', methods=['POST'])
@login_required
def expire_code(event_id):
    """Expire the attendance code (coordinator/admin)."""
    role = session.get('role')
    if role not in ('admin', 'club_admin'):
        flash("Permission denied.", "danger")
        return redirect(url_for('events.detail', event_id=event_id))
    try:
        expire_attendance_code(event_id)
        flash("Attendance code has been expired. Students can no longer submit.", "success")
    except Exception as e:
        flash(f"Error expiring code: {e}", "danger")
    return redirect(url_for('attendance.show_code', event_id=event_id))


@bp.route('/mark/<int:event_id>', methods=['GET', 'POST'])
@login_required
def mark(event_id):
    """
    Admin / Club Coordinator marks attendance for a student manually.
    GET  → show the mark attendance form
    POST → validate code + student identifier, mark attendance
    """
    role = session.get('role')
    if role not in ('admin', 'club_admin'):
        flash("Only admins/club coordinators can mark attendance.", "danger")
        return redirect(url_for('events.detail', event_id=event_id))

    event = get_event_by_id(event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('events.list_events'))

    records = get_attendance_for_event(event_id)
    user    = get_user_by_id(session['user_id'])

    if request.method == 'POST':
        code       = request.form.get('attendance_code', '').strip()
        identifier = request.form.get('student_identifier', '').strip()

        if not code or not identifier:
            flash("Both attendance code and student email/ID are required.", "danger")
        else:
            result = mark_attendance_by_code(code, identifier, marked_by=session['user_id'])
            if result['success']:
                flash(result['message'], "success")
                records = get_attendance_for_event(event_id)
            else:
                flash(result['message'], "danger")

    return render_template('attendance/mark.html',
                           event=event, attendance_records=records,
                           user=user, active='events')


@bp.route('/mark/<int:event_id>/ajax', methods=['POST'])
@login_required
def mark_ajax(event_id):
    """AJAX endpoint for real-time attendance marking by coordinator."""
    role = session.get('role')
    if role not in ('admin', 'club_admin'):
        return jsonify({'success': False, 'message': 'Permission denied.'})

    data       = request.get_json(force=True) or {}
    code       = data.get('attendance_code', '').strip()
    identifier = data.get('student_identifier', '').strip()

    if not code or not identifier:
        return jsonify({'success': False, 'message': 'Code and student identifier required.'})

    result = mark_attendance_by_code(code, identifier, marked_by=session['user_id'])
    return jsonify(result)
