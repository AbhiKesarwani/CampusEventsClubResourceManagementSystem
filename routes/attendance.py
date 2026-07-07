# routes/attendance.py
import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from helpers.auth_helpers import login_required
from helpers.qr_helpers import make_qr_payload, verify_qr_payload, generate_qr_image
from services.user_service import get_user_by_id
from services.event_service import get_event_by_id
from services.attendance_service import mark_attendance, get_attendance_for_event, has_attended

bp = Blueprint('attendance', __name__, url_prefix='/attendance')

QR_FOLDER = os.getenv('QR_FOLDER', 'static/qrcodes')


@bp.route('/qr/<int:event_id>')
@login_required
def show_qr(event_id):
    """Student views their attendance QR for a specific event."""
    event = get_event_by_id(event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('events.list_events'))

    user_id = session['user_id']
    payload = make_qr_payload(event_id, user_id)

    os.makedirs(QR_FOLDER, exist_ok=True)
    qr_filename = f"qr_{event_id}_{user_id}.png"
    qr_path     = os.path.join(QR_FOLDER, qr_filename)
    generate_qr_image(payload, qr_path)

    qr_url   = f"/static/qrcodes/{qr_filename}"
    attended = has_attended(event_id, user_id)
    user     = get_user_by_id(user_id)

    return render_template('attendance/qr.html',
                           event=event, qr_url=qr_url, attended=attended,
                           user=user, active='events')


@bp.route('/scan/<int:event_id>', methods=['GET', 'POST'])
@login_required
def scan(event_id):
    """
    Admin / volunteer scans or manually enters QR payload to mark attendance.
    """
    role = session.get('role')
    if role not in ('admin', 'club_admin'):
        flash("Only admins/club admins can scan attendance.", "danger")
        return redirect(url_for('events.detail', event_id=event_id))

    event   = get_event_by_id(event_id)
    records = get_attendance_for_event(event_id)
    user    = get_user_by_id(session['user_id'])

    if request.method == 'POST':
        payload = request.form.get('qr_payload', '').strip()
        try:
            data = verify_qr_payload(payload)
            if data['event_id'] != event_id:
                flash("QR code is for a different event.", "danger")
            else:
                is_new = mark_attendance(event_id, data['user_id'], scan_by=session['user_id'])
                if is_new:
                    flash("✅ Attendance marked successfully!", "success")
                else:
                    flash("Attendance already recorded for this user.", "warning")
                records = get_attendance_for_event(event_id)
        except ValueError as e:
            flash(f"Invalid QR: {e}", "danger")

    return render_template('attendance/scan.html',
                           event=event, attendance_records=records,
                           user=user, active='events')


@bp.route('/mark/<int:event_id>', methods=['POST'])
@login_required
def self_mark(event_id):
    """Student self-marks attendance by submitting their QR payload."""
    payload = request.form.get('qr_payload', '').strip()
    try:
        data = verify_qr_payload(payload)
        if data['user_id'] != session['user_id']:
            flash("Invalid QR payload.", "danger")
        elif data['event_id'] != event_id:
            flash("QR code is for a different event.", "danger")
        else:
            is_new = mark_attendance(event_id, session['user_id'])
            flash("✅ Attendance marked!" if is_new else "Already marked.", "success" if is_new else "info")
    except ValueError as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for('attendance.show_qr', event_id=event_id))
