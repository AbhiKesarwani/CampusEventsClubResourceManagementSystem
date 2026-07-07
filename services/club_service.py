# services/club_service.py
from database import get_db_connection


def get_all_clubs() -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT c.*,
                   u.name AS coordinator_name,
                   (SELECT img_path FROM club_images
                    WHERE club_id = c.club_id ORDER BY img_id ASC LIMIT 1) AS first_image,
                   (SELECT COUNT(*) FROM events e WHERE e.club_id = c.club_id) AS event_count,
                   (SELECT COUNT(*) FROM club_members m WHERE m.club_id = c.club_id) AS member_count
            FROM clubs c
            LEFT JOIN users u ON c.coordinator_id = u.user_id
            ORDER BY c.club_name ASC
        """)
        return cur.fetchall()
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


def set_club_coordinator(club_id: int, user_id: int | None) -> None:
    """Update a club's coordinator_id and record the assignment timestamp."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        if user_id is not None:
            cur.execute(
                "UPDATE clubs SET coordinator_id=%s, assigned_at=NOW() WHERE club_id=%s",
                (user_id, club_id)
            )
        else:
            cur.execute(
                "UPDATE clubs SET coordinator_id=NULL, assigned_at=NULL WHERE club_id=%s",
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
    """Return all clubs that have a coordinator assigned, with user details."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT c.club_id, c.club_name, c.assigned_at,
                   u.user_id AS coordinator_id,
                   u.name    AS coordinator_name,
                   u.email   AS coordinator_email,
                   u.role    AS coordinator_role
            FROM clubs c
            LEFT JOIN users u ON c.coordinator_id = u.user_id
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
