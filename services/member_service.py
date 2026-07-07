# services/member_service.py
from database import get_db_connection

POSITION_ORDER = {
    'President': 1, 'Vice President': 2, 'Secretary': 3,
    'Treasurer': 4, 'Coordinator': 5, 'Volunteer': 6, 'Member': 7
}


def get_club_members(club_id: int) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT cm.*, u.name, u.email,
                   cm.position,
                   cm.joined_at
            FROM club_members cm
            JOIN users u ON cm.user_id = u.user_id
            WHERE cm.club_id = %s
            ORDER BY FIELD(cm.position,
                'President','Vice President','Secretary','Treasurer',
                'Coordinator','Volunteer','Member'), u.name
        """, (club_id,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_non_members(club_id: int) -> list[dict]:
    """Return users who are NOT already members of the club."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT u.user_id, u.name, u.email, u.role
            FROM users u
            WHERE u.user_id NOT IN (
                SELECT user_id FROM club_members WHERE club_id = %s
            )
            ORDER BY u.name
        """, (club_id,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def add_member(club_id: int, user_id: int, position: str = 'Member') -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO club_members (club_id, user_id, position)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE position = VALUES(position)
        """, (club_id, user_id, position))
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def remove_member(club_id: int, user_id: int) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM club_members WHERE club_id=%s AND user_id=%s",
                    (club_id, user_id))
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def change_position(club_id: int, user_id: int, position: str) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE club_members SET position=%s WHERE club_id=%s AND user_id=%s",
            (position, club_id, user_id)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def is_member(club_id: int, user_id: int) -> bool:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "SELECT 1 FROM club_members WHERE club_id=%s AND user_id=%s LIMIT 1",
            (club_id, user_id)
        )
        return cur.fetchone() is not None
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_member_count(club_id: int) -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM club_members WHERE club_id=%s", (club_id,))
        row = cur.fetchone()
        return row[0] if row else 0
    finally:
        if cur: cur.close()
        if conn: conn.close()
