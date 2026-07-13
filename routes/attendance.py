# routes/attendance.py
from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash, jsonify)
from helpers.auth_helpers import login_required
from services.user_service import get_user_by_id
from services.event_service import get_event_by_id
from services.attendance_service import (
    generate_attendance_code, get_event_by_attendance_code,
    mark_attendance_by_code, mark_attendance,
    get_attendance_for_event, has_attended,
    submit_code_self, get_upcoming_events_for_user,
    get_student_attendance_history, expire_attendance_code,
    # OTP
    generate_otp, get_event_by_otp, submit_otp_self,
)

bp = Blueprint('attendance', __name__, url_prefix='/attendance')

OTP_EXPIRY_MINUTES = 5


# ──────────────────────────────────────────────────────────────────────────────
#  STUDENT ROUTES
# ──────────────────────────────────────────────────────────────────────────────

@bp.route('/my')
@login_required
def my_attendance():
    """Student: view active OTPs + submit + attendance history."""
    user_id = session['user_id']
    user    = get_user_by_id(user_id)
    active_events = get_upcoming_events_for_user(user_id)
    history       = get_student_attendance_history(user_id)
    return render_template('attendance/my.html',
                           active_events=active_events,
                           history=history,
                           user=user,
                           active='attendance',
                           otp_expiry_minutes=OTP_EXPIRY_MINUTES)


@bp.route('/submit', methods=['POST'])
@login_required
def submit_code():
    """Student submits a 6-digit OTP (AJAX or form POST)."""
    user_id = session['user_id']
    is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest'
               or request.is_json)

    if is_ajax:
        data = request.get_json(force=True) or {}
        # Accept both 'code' (legacy) and 'otp'
        otp = (data.get('otp') or data.get('code') or '').strip()
        if not otp:
            return jsonify({'success': False, 'message': 'Please enter a 6-digit OTP.'})
        result = submit_otp_self(otp, user_id)
        return jsonify(result)

    otp = (request.form.get('otp') or request.form.get('code') or '').strip()
    if not otp:
        flash('Please enter a 6-digit OTP.', 'danger')
        return redirect(url_for('attendance.my_attendance'))

    result = submit_otp_self(otp, user_id)
    flash(result['message'], 'success' if result['success'] else 'danger')
    return redirect(url_for('attendance.my_attendance'))


# ──────────────────────────────────────────────────────────────────────────────
#  COORDINATOR / ADMIN ROUTES
# ──────────────────────────────────────────────────────────────────────────────

@bp.route('/code/<int:event_id>')
@login_required
def show_code(event_id):
    """Admin or Club Coordinator: view/generate OTP for an event."""
    role = session.get('role')
    if role not in ('admin', 'club_admin'):
        flash("Only admins/club coordinators can manage attendance OTPs.", "danger")
        return redirect(url_for('events.detail', event_id=event_id))

    event = get_event_by_id(event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('events.list_events'))

    records = get_attendance_for_event(event_id)
    user    = get_user_by_id(session['user_id'])

    # OTP status
    from datetime import datetime, timedelta
    otp_active  = False
    otp_seconds = 0
    gen_at = event.get('otp_generated_at')
    if gen_at and event.get('attendance_otp'):
        if isinstance(gen_at, str):
            try:
                gen_at = datetime.fromisoformat(gen_at)
            except ValueError:
                gen_at = None
        if gen_at:
            elapsed  = (datetime.now() - gen_at).total_seconds()
            remaining = OTP_EXPIRY_MINUTES * 60 - elapsed
            if remaining > 0:
                otp_active  = True
                otp_seconds = int(remaining)

    return render_template('attendance/code.html',
                           event=event,
                           attendance_records=records,
                           user=user,
                           otp_active=otp_active,
                           otp_seconds=otp_seconds,
                           otp_expiry_minutes=OTP_EXPIRY_MINUTES,
                           active='events')


@bp.route('/code/<int:event_id>/generate-otp', methods=['POST'])
@login_required
def generate_event_otp(event_id):
    """Generate / regenerate a 6-digit OTP for an event."""
    role = session.get('role')
    if role not in ('admin', 'club_admin'):
        flash("Permission denied.", "danger")
        return redirect(url_for('events.detail', event_id=event_id))
    try:
        otp = generate_otp(event_id)
        flash(f"OTP generated: {otp} — valid for {OTP_EXPIRY_MINUTES} minutes.", "success")
    except Exception as e:
        flash(f"Error generating OTP: {e}", "danger")
    return redirect(url_for('attendance.show_code', event_id=event_id))


@bp.route('/code/<int:event_id>/regenerate', methods=['POST'])
@login_required
def regenerate_code(event_id):
    """Regenerate OTP (alias route kept for backward compat)."""
    return generate_event_otp(event_id)


@bp.route('/code/<int:event_id>/expire', methods=['POST'])
@login_required
def expire_code(event_id):
    """Expire the current OTP immediately."""
    role = session.get('role')
    if role not in ('admin', 'club_admin'):
        flash("Permission denied.", "danger")
        return redirect(url_for('events.detail', event_id=event_id))
    try:
        expire_attendance_code(event_id)
        flash("OTP has been expired. Students can no longer submit.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for('attendance.show_code', event_id=event_id))


@bp.route('/mark/<int:event_id>', methods=['GET', 'POST'])
@login_required
def mark(event_id):
    """Admin / Coordinator: manually mark attendance for a student."""
    role = session.get('role')
    if role not in ('admin', 'club_admin'):
        flash("Only admins/club coordinators can mark attendance.", "danger")
        return redirect(url_for('events.detail', event_id=event_id))

    event   = get_event_by_id(event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('events.list_events'))

    records = get_attendance_for_event(event_id)
    user    = get_user_by_id(session['user_id'])

    if request.method == 'POST':
        code       = request.form.get('attendance_code', '').strip()
        identifier = request.form.get('student_identifier', '').strip()
        if not code or not identifier:
            flash("Both OTP/code and student email/ID are required.", "danger")
        else:
            result = mark_attendance_by_code(code, identifier,
                                            marked_by=session['user_id'])
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
    """AJAX endpoint for coordinator real-time marking."""
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
