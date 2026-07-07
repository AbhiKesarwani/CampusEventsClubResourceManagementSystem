# services/membership_service.py
from database import get_db_connection
from services.member_service import add_member


def request_join(club_id: int, user_id: int) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO membership_requests (club_id, user_id, status)
            VALUES (%s, %s, 'Pending')
            ON DUPLICATE KEY UPDATE status = IF(status='Rejected','Pending',status)
        """, (club_id, user_id))
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_requests_for_club(club_id: int, status: str = None) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        if status:
            cur.execute("""
                SELECT mr.*, u.name AS student_name, u.email AS student_email,
                       c.club_name
                FROM membership_requests mr
                JOIN users u ON mr.user_id = u.user_id
                JOIN clubs c ON mr.club_id = c.club_id
                WHERE mr.club_id = %s AND mr.status = %s
                ORDER BY mr.created_at DESC
            """, (club_id, status))
        else:
            cur.execute("""
                SELECT mr.*, u.name AS student_name, u.email AS student_email,
                       c.club_name
                FROM membership_requests mr
                JOIN users u ON mr.user_id = u.user_id
                JOIN clubs c ON mr.club_id = c.club_id
                WHERE mr.club_id = %s
                ORDER BY mr.created_at DESC
            """, (club_id,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_user_request_status(club_id: int, user_id: int) -> str | None:
    """Return 'Pending', 'Approved', 'Rejected', or None."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT status FROM membership_requests WHERE club_id=%s AND user_id=%s LIMIT 1",
            (club_id, user_id)
        )
        row = cur.fetchone()
        return row['status'] if row else None
    finally:
        if cur: cur.close()
        if conn: conn.close()


def approve_request(request_id: int, reviewer_id: int) -> dict:
    """Approve request and auto-add user as club member."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM membership_requests WHERE request_id=%s", (request_id,))
        req = cur.fetchone()
        if not req:
            raise ValueError("Request not found.")

        cur.execute(
            "UPDATE membership_requests SET status='Approved' WHERE request_id=%s",
            (request_id,)
        )
        conn.commit()

        # Auto-add as Member
        add_member(req['club_id'], req['user_id'], 'Member')
        return req
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def reject_request(request_id: int, reviewer_id: int) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE membership_requests SET status='Rejected' WHERE request_id=%s",
            (request_id,)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def count_pending_requests_for_club(club_id: int) -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM membership_requests WHERE club_id=%s AND status='Pending'",
            (club_id,)
        )
        row = cur.fetchone()
        return row[0] if row else 0
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_all_pending_requests(coordinator_email: str) -> list[dict]:
    """Get all pending requests for clubs owned by a coordinator email."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT mr.*, u.name AS student_name, u.email AS student_email,
                   c.club_name, c.club_id
            FROM membership_requests mr
            JOIN users u ON mr.user_id = u.user_id
            JOIN clubs c ON mr.club_id = c.club_id
            WHERE mr.status = 'Pending'
              AND LOWER(c.club_email) = LOWER(%s)
            ORDER BY mr.created_at DESC
        """, (coordinator_email,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()
