# routes/certificates.py
import os
from flask import Blueprint, render_template, request, session, flash, redirect, url_for, send_file
from helpers.auth_helpers import login_required, admin_required
from services.user_service import get_user_by_id
from services.certificate_service import (
    get_user_certificates, issue_certificate, certificate_exists
)
from services.attendance_service import has_attended, get_attendance_for_event
from services.event_service import get_event_by_id
from services.log_service import log_action

bp = Blueprint('certificates', __name__, url_prefix='/certificates')

PER_PAGE = 12


@bp.route('/my')
@login_required
def my_certificates():
    page      = request.args.get('page', 1, type=int)
    user      = get_user_by_id(session['user_id'])
    all_certs = get_user_certificates(session['user_id'])
    total     = len(all_certs)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page      = max(1, min(page, total_pages))
    offset    = (page - 1) * PER_PAGE
    certs     = all_certs[offset: offset + PER_PAGE]
    return render_template('certificates/list.html',
                           certificates=certs, user=user, active='certificates',
                           page=page, total_pages=total_pages, total=total)


@bp.route('/generate/<int:event_id>/<int:user_id>', methods=['POST'])
@admin_required
def generate(event_id, user_id):
    """Admin generates certificate for a specific user who attended an event."""
    event  = get_event_by_id(event_id)
    target = get_user_by_id(user_id)
    if not event or not target:
        flash("Event or user not found.", "danger")
        return redirect(url_for('attendance.scan', event_id=event_id))

    if not has_attended(event_id, user_id):
        flash("User has not attended this event.", "danger")
        return redirect(url_for('attendance.scan', event_id=event_id))

    try:
        cert = issue_certificate(event_id, user_id, target['name'], event['title'])
        log_action(session['user_id'], 'GENERATE_CERTIFICATE', 'certificate', cert['cert_id'],
                   f"{target['name']} | {event['title']}")
        flash(f"Certificate generated for {target['name']}!", "success")
    except Exception as e:
        flash(f"Error generating certificate: {e}", "danger")

    return redirect(url_for('attendance.scan', event_id=event_id))


@bp.route('/self_generate/<int:event_id>', methods=['POST'])
@login_required
def self_generate(event_id):
    """Student self-generates their own certificate after attending."""
    user_id = session['user_id']
    event   = get_event_by_id(event_id)
    user    = get_user_by_id(user_id)

    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('certificates.my_certificates'))

    if not has_attended(event_id, user_id):
        flash("You have not marked attendance for this event.", "danger")
        return redirect(url_for('certificates.my_certificates'))

    try:
        issue_certificate(event_id, user_id, user['name'], event['title'])
        flash("Certificate generated! You can now download it.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")

    return redirect(url_for('certificates.my_certificates'))


@bp.route('/download/<int:cert_id>')
@login_required
def download(cert_id):
    """Download a certificate file. Users can only download their own."""
    from database import get_db_connection
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM certificates WHERE cert_id=%s", (cert_id,))
        cert = cur.fetchone()
    finally:
        if cur: cur.close()
        if conn: conn.close()

    if not cert:
        flash("Certificate not found.", "danger")
        return redirect(url_for('certificates.my_certificates'))

    role = session.get('role')
    if role != 'admin' and cert['user_id'] != session['user_id']:
        flash("Access denied.", "danger")
        return redirect(url_for('certificates.my_certificates'))

    full_path = os.path.join('static', cert['cert_path'])
    if not os.path.exists(full_path):
        flash("Certificate file missing. Please regenerate.", "warning")
        return redirect(url_for('certificates.my_certificates'))

    return send_file(full_path, as_attachment=True,
                     download_name=f"certificate_{cert_id}.png")


# ── Public Verification (no login required) ────────────────────────────────────

@bp.route('/verify/<int:cert_id>')
def verify(cert_id):
    """Public certificate verification page."""
    from database import get_db_connection
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT ce.cert_id, ce.issue_date, ce.cert_path,
                   u.name AS student_name,
                   e.title AS event_title, e.date AS event_date,
                   c.club_name
            FROM certificates ce
            JOIN users  u ON ce.user_id  = u.user_id
            JOIN events e ON ce.event_id = e.event_id
            LEFT JOIN clubs c ON e.club_id = c.club_id
            WHERE ce.cert_id = %s
        """, (cert_id,))
        cert = cur.fetchone()
    finally:
        if cur: cur.close()
        if conn: conn.close()

    if not cert:
        return render_template('certificates/verify.html', cert=None, valid=False)

    valid = bool(cert.get('cert_path'))
    return render_template('certificates/verify.html', cert=cert, valid=valid)

