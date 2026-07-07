# services/attendance_service.py
from database import get_db_connection


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

