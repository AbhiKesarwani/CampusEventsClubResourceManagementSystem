# services/club_service.py
from database import get_db_connection


def get_all_clubs(search=None, coordinator_id=None, has_events=None) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        query = """
            SELECT c.*,
                   u.name AS coordinator_name,
                   (SELECT img_path FROM club_images
                    WHERE club_id = c.club_id ORDER BY img_id ASC LIMIT 1) AS first_image,
                   (SELECT COUNT(*) FROM events e WHERE e.club_id = c.club_id) AS event_count,
                   (SELECT COUNT(*) FROM events e WHERE e.club_id = c.club_id AND e.date >= CURDATE()) AS upcoming_event_count,
                   (SELECT COUNT(*) FROM club_members m WHERE m.club_id = c.club_id) AS member_count
            FROM clubs c
            LEFT JOIN users u ON c.coordinator_id = u.user_id
            WHERE 1=1
        """
        params = []
        if search:
            query += " AND c.club_name LIKE %s"
            params.append(f"%{search}%")
        if coordinator_id:
            query += " AND c.coordinator_id = %s"
            params.append(coordinator_id)
        if has_events:
            query += " AND (SELECT COUNT(*) FROM events e WHERE e.club_id = c.club_id) > 0"
        query += " ORDER BY c.club_name ASC"
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def count_all_clubs(search=None, coordinator_id=None, has_events=None) -> int:
    """Count clubs matching optional filters (for pagination)."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        query = "SELECT COUNT(*) FROM clubs c WHERE 1=1"
        params = []
        if search:
            query += " AND c.club_name LIKE %s"
            params.append(f"%{search}%")
        if coordinator_id:
            query += " AND c.coordinator_id = %s"
            params.append(coordinator_id)
        if has_events:
            query += " AND (SELECT COUNT(*) FROM events e WHERE e.club_id = c.club_id) > 0"
        cur.execute(query, params)
        row = cur.fetchone()
        return row[0] if row else 0
    finally:
        if cur: cur.close()
        if conn: conn.close()



def get_club_by_id(club_id: int) -> dict | None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT c.*, u.name AS coordinator_name
            FROM clubs c
            LEFT JOIN users u ON c.coordinator_id = u.user_id
            WHERE c.club_id = %s
        """, (club_id,))
        return cur.fetchone()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_club_by_email(email: str) -> dict | None:
    """Find club where club_email matches (case-insensitive)."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM clubs WHERE LOWER(club_email) = LOWER(%s) LIMIT 1",
            (email,)
        )
        return cur.fetchone()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_club_images(club_id: int) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM club_images WHERE club_id = %s ORDER BY img_id ASC", (club_id,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def create_club(club_name: str, description: str,
                coordinator_id: int = None, club_email: str = None) -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO clubs (club_name, description, coordinator_id, club_email) VALUES (%s,%s,%s,%s)",
            (club_name, description, coordinator_id, club_email)
        )
        conn.commit()
        return cur.lastrowid
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def update_club(club_id: int, club_name: str, description: str,
                club_email: str = None) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE clubs SET club_name=%s, description=%s, club_email=%s WHERE club_id=%s",
            (club_name, description, club_email, club_id)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def delete_club(club_id: int) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM clubs WHERE club_id = %s", (club_id,))
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def add_club_image(club_id: int, img_path: str) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("INSERT INTO club_images (club_id, img_path) VALUES (%s,%s)", (club_id, img_path))
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def delete_club_image(img_id: int) -> str | None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT img_path FROM club_images WHERE img_id=%s", (img_id,))
        row = cur.fetchone()
        if row:
            cur.execute("DELETE FROM club_images WHERE img_id=%s", (img_id,))
            conn.commit()
            return row['img_path']
        return None
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_clubs_for_select() -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT club_id, club_name FROM clubs ORDER BY club_name")
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def set_club_coordinator(club_id: int, user_id: int | None,
                         assigned_by_id: int | None = None) -> None:
    """Update a club's coordinator, assignment timestamp, and assigning admin.

    Args:
        club_id:        The club to update.
        user_id:        The new coordinator's user_id, or None to clear.
        assigned_by_id: The admin user_id who is making the assignment,
                        or None when clearing.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        if user_id is not None:
            cur.execute(
                """UPDATE clubs
                   SET coordinator_id = %s,
                       assigned_at    = NOW(),
                       assigned_by    = %s
                   WHERE club_id = %s""",
                (user_id, assigned_by_id, club_id)
            )
        else:
            cur.execute(
                """UPDATE clubs
                   SET coordinator_id = NULL,
                       assigned_at    = NULL,
                       assigned_by    = NULL
                   WHERE club_id = %s""",
                (club_id,)
            )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_coordinator_directory() -> list[dict]:
    """Return ALL clubs with coordinator info, including assigning admin name."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT
                c.club_id,
                c.club_name,
                c.assigned_at,
                c.coordinator_id,
                u.name    AS coordinator_name,
                u.email   AS coordinator_email,
                u.role    AS coordinator_role,
                ab.name   AS assigned_by_name
            FROM clubs c
            LEFT JOIN users u  ON c.coordinator_id = u.user_id
            LEFT JOIN users ab ON c.assigned_by     = ab.user_id
            ORDER BY c.club_name ASC
        """)
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_all_clubs_with_coordinator_status() -> list[dict]:
    """Return all clubs with coordinator info — used for assignment panel."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT c.*,
                   u.name  AS coordinator_name,
                   u.email AS coordinator_email,
                   (SELECT img_path FROM club_images
                    WHERE club_id = c.club_id ORDER BY img_id ASC LIMIT 1) AS first_image
            FROM clubs c
            LEFT JOIN users u ON c.coordinator_id = u.user_id
            ORDER BY c.club_name ASC
        """)
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()
