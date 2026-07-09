# services/user_service.py
from database import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash


def get_user_by_id(uid: int) -> dict | None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE user_id = %s", (uid,))
        return cur.fetchone()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_user_by_email(email: str) -> dict | None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        return cur.fetchone()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_all_users() -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT user_id, name, email, role, phone, club_id, created_at FROM users ORDER BY name")
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def create_user(name: str, email: str, password: str,
                phone: str = None, club_id: int = None, role: str = 'student') -> int:
    pw_hash = generate_password_hash(password)
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO users (name, email, password_hash, phone, club_id, role) VALUES (%s,%s,%s,%s,%s,%s)",
            (name, email, pw_hash, phone, club_id, role)
        )
        conn.commit()
        return cur.lastrowid
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def verify_password(user: dict, password: str) -> bool:
    return check_password_hash(user['password_hash'], password)


def assign_coordinator(user_id: int, club_id: int) -> None:
    """Set a user as club_admin for a specific club."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE users SET role='club_admin', club_id=%s WHERE user_id=%s",
            (club_id, user_id)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def remove_coordinator(user_id: int) -> None:
    """Reset a club_admin back to student, clearing their club assignment."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE users SET role='student', club_id=NULL WHERE user_id=%s",
            (user_id,)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_students_for_select() -> list[dict]:
    """Return all non-admin users for coordinator selection.

    Excludes admins (cannot be assigned as coordinators).
    Includes club_admin and student roles.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT user_id, name, email, role, club_id
               FROM users
               WHERE role != 'admin'
               ORDER BY name"""
        )
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def search_users_for_coordinator(query: str) -> list[dict]:
    """Search non-admin users by name or email (AJAX endpoint).

    Returns up to 20 matches.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        like = f"%{query}%"
        cur.execute(
            """SELECT user_id, name, email, role, club_id
               FROM users
               WHERE role != 'admin'
                 AND (name LIKE %s OR email LIKE %s)
               ORDER BY name
               LIMIT 20""",
            (like, like)
        )
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()
