# services/attendance_service.py
import random
import string
from datetime import datetime, timedelta
from database import get_db_connection


def _generate_code() -> str:
    """Generate a unique attendance code in format AAG-483921."""
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    digits  = ''.join(random.choices(string.digits, k=6))
    return f"{letters}-{digits}"


def _generate_otp_digits() -> str:
    """Generate a 6-digit numeric OTP."""
    return f"{random.randint(0, 999999):06d}"


def generate_otp(event_id: int) -> str:
    """
    Generate (or regenerate) a 6-digit numeric OTP for an event.
    OTP expires 5 minutes after generation.
    Stores in attendance_otp + otp_generated_at on the events table.
    Returns the OTP string.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        otp       = _generate_otp_digits()
        generated = datetime.now()
        cur.execute(
            "UPDATE events SET attendance_otp=%s, otp_generated_at=%s WHERE event_id=%s",
            (otp, generated, event_id)
        )
        conn.commit()
        return otp
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_event_by_otp(otp: str) -> dict | None:
    """
    Look up an event by its 6-digit OTP.
    Returns None if not found OR if OTP is older than 5 minutes.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM events WHERE attendance_otp = %s",
            (otp.strip(),)
        )
        event = cur.fetchone()
        if not event:
            return None
        # 5-minute expiry check
        gen_at = event.get('otp_generated_at')
        if gen_at:
            if isinstance(gen_at, str):
                try:
                    gen_at = datetime.fromisoformat(gen_at)
                except ValueError:
                    gen_at = None
            if gen_at and datetime.now() - gen_at > timedelta(minutes=5):
                return None  # expired
        return event
    finally:
        if cur: cur.close()
        if conn: conn.close()


def submit_otp_self(otp: str, user_id: int) -> dict:
    """
    Student self-submits a 6-digit OTP.
    Returns {success, message, event_title, cert_path (if issued)}
    """
    otp = otp.strip()
    event = get_event_by_otp(otp)
    if not event:
        return {'success': False,
                'message': 'Invalid or expired OTP. OTPs are valid for 5 minutes only.'}

    is_new = mark_attendance(event['event_id'], user_id, scan_by=None)
    if not is_new:
        return {'success': False,
                'message': 'You have already submitted attendance for this event.'}

    # Auto-generate certificate
    cert_path = None
    try:
        from services.certificate_service import issue_certificate
        from services.user_service import get_user_by_id
        student = get_user_by_id(user_id)
        if student:
            cert = issue_certificate(
                event['event_id'], user_id,
                student['name'], event['title']
            )
            cert_path = cert.get('cert_path') if cert else None
    except Exception:
        pass  # certificate failure must never block attendance

    # Dedup notification to student
    try:
        from services.notification_service import create_notification_safe
        create_notification_safe(
            user_id=user_id,
            title='Attendance Marked ✓',
            body=f"Your attendance for '{event['title']}' has been recorded.",
            link='/attendance/my',
            type='attendance_marked',
            event_key=f"att_{event['event_id']}_{user_id}"
        )
    except Exception:
        pass

    return {
        'success':     True,
        'message':     f"Attendance marked for \u201c{event['title']}\u201d!",
        'event_title': event['title'],
        'cert_path':   cert_path
    }



def get_event_by_attendance_code(code: str) -> dict | None:
    """Look up an event by its attendance code. Returns None if not found or expired."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM events WHERE attendance_code = %s",
            (code.strip().upper(),)
        )
        event = cur.fetchone()
        if not event:
            return None
        # Check expiry
        if event.get('code_expires_at') and event['code_expires_at'] < datetime.now():
            return None  # expired
        return event
    finally:
        if cur: cur.close()
        if conn: conn.close()


def mark_attendance(event_id: int, user_id: int, scan_by: int = None) -> bool:
    """
    Insert attendance record. Returns True if new, False if already marked.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "SELECT attendance_id FROM attendance WHERE event_id=%s AND user_id=%s",
            (event_id, user_id)
        )
        if cur.fetchone():
            return False  # already marked
        cur.execute(
            "INSERT INTO attendance (event_id, user_id, scan_by) VALUES (%s,%s,%s)",
            (event_id, user_id, scan_by)
        )
        conn.commit()
        return True
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def mark_attendance_by_code(code: str, identifier: str, marked_by: int) -> dict:
    """
    Mark attendance using an attendance code + student email or student ID.
    Returns dict with keys: success, message, user_name.
    """
    from services.user_service import get_user_by_email, get_user_by_id as _get_user

    event = get_event_by_attendance_code(code)
    if not event:
        return {'success': False, 'message': 'Invalid or expired attendance code.'}

    # Resolve student
    student = None
    identifier = identifier.strip()
    if '@' in identifier:
        student = get_user_by_email(identifier)
    else:
        try:
            student = _get_user(int(identifier))
        except (ValueError, TypeError):
            pass

    if not student:
        return {'success': False, 'message': 'Student not found. Check email or ID.'}

    if student.get('role') != 'student':
        return {'success': False, 'message': 'Only students can have attendance marked.'}

    is_new = mark_attendance(event['event_id'], student['user_id'], scan_by=marked_by)
    if is_new:
        return {'success': True, 'message': f"Attendance marked for {student['name']}.",
                'user_name': student['name']}
    else:
        return {'success': False, 'message': f"{student['name']} already has attendance recorded."}


def get_attendance_for_event(event_id: int) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT a.*, u.name, u.email
            FROM attendance a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.event_id = %s
            ORDER BY a.scan_time ASC
        """, (event_id,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_user_attendance(user_id: int) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT a.*, e.title, e.date, c.club_name
            FROM attendance a
            JOIN events e ON a.event_id = e.event_id
            LEFT JOIN clubs c ON e.club_id = c.club_id
            WHERE a.user_id = %s
            ORDER BY a.scan_time DESC
        """, (user_id,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def has_attended(event_id: int, user_id: int) -> bool:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "SELECT 1 FROM attendance WHERE event_id=%s AND user_id=%s",
            (event_id, user_id)
        )
        return cur.fetchone() is not None
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_all_attendance_records(limit: int = 5000) -> list[dict]:
    """System-wide attendance records for admin exports."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT a.attendance_id, u.name AS student_name, u.email AS student_email,
                   e.title AS event_title, c.club_name, a.scan_time
            FROM attendance a
            JOIN users u  ON a.user_id  = u.user_id
            JOIN events e ON a.event_id = e.event_id
            LEFT JOIN clubs c ON e.club_id = c.club_id
            ORDER BY a.scan_time DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_upcoming_events_for_user(user_id: int) -> list:
    """
    Return events that:
    - Have an active (non-expired) attendance code
    - The student has NOT already attended
    Ordered by date ascending.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT e.event_id, e.title, e.date, e.start_time,
                   e.attendance_code, e.code_expires_at,
                   c.club_name,
                   v.venue_name,
                   EXISTS(
                       SELECT 1 FROM attendance a
                       WHERE a.event_id = e.event_id AND a.user_id = %s
                   ) AS already_attended
            FROM events e
            LEFT JOIN clubs  c ON e.club_id  = c.club_id
            LEFT JOIN venues v ON e.venue_id = v.venue_id
            WHERE e.attendance_code IS NOT NULL
              AND (
                  e.code_expires_at IS NULL
                  OR e.code_expires_at > NOW()
              )
            ORDER BY e.date ASC, e.start_time ASC
        """, (user_id,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_student_attendance_history(user_id: int) -> list:
    """
    Full attendance history for a student, newest first.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT a.attendance_id, a.scan_time,
                   e.event_id, e.title, e.date,
                   c.club_name
            FROM attendance a
            JOIN events e ON a.event_id = e.event_id
            LEFT JOIN clubs c ON e.club_id = c.club_id
            WHERE a.user_id = %s
            ORDER BY a.scan_time DESC
        """, (user_id,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def expire_attendance_code(event_id: int) -> bool:
    """
    Mark the attendance code as expired by setting code_expires_at to now().
    Returns True on success.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE events SET code_expires_at = NOW() WHERE event_id = %s",
            (event_id,)
        )
        conn.commit()
        return True
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def count_attendance() -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM attendance")
        return cur.fetchone()[0]
    finally:
        if cur: cur.close()
        if conn: conn.close()


# ─── Analytics ────────────────────────────────────────────────────────────────

def get_top_events_by_attendance(limit: int = 5) -> list[dict]:
    """Most attended events (for admin dashboard chart)."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT e.title, COUNT(a.attendance_id) AS count
            FROM attendance a
            JOIN events e ON a.event_id = e.event_id
            GROUP BY a.event_id
            ORDER BY count DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_top_clubs_by_attendance(limit: int = 5) -> list[dict]:
    """Most active clubs by total attendance."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT c.club_name, COUNT(a.attendance_id) AS count
            FROM attendance a
            JOIN events e ON a.event_id = e.event_id
            JOIN clubs c ON e.club_id = c.club_id
            GROUP BY c.club_id
            ORDER BY count DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_top_students_by_attendance(limit: int = 5) -> list[dict]:
    """Most active students by attendance count."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT u.name, COUNT(a.attendance_id) AS count
            FROM attendance a
            JOIN users u ON a.user_id = u.user_id
            GROUP BY a.user_id
            ORDER BY count DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_club_monthly_attendance(club_id: int, months: int = 6) -> list[dict]:
    """Monthly attendance count for a club's events (for club_admin chart)."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT DATE_FORMAT(a.scan_time, '%%Y-%%m') AS month,
                   COUNT(a.attendance_id) AS count
            FROM attendance a
            JOIN events e ON a.event_id = e.event_id
            WHERE e.club_id = %s
              AND a.scan_time >= DATE_SUB(NOW(), INTERVAL %s MONTH)
            GROUP BY month
            ORDER BY month ASC
        """, (club_id, months))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_most_attended_event() -> dict | None:
    """Single most attended event for admin stats."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT e.title, COUNT(a.attendance_id) AS count
            FROM attendance a
            JOIN events e ON a.event_id = e.event_id
            GROUP BY a.event_id
            ORDER BY count DESC
            LIMIT 1
        """)
        return cur.fetchone()
    finally:
        if cur: cur.close()
        if conn: conn.close()
