# services/notification_service.py
from database import get_db_connection


def create_notification(user_id: int, title: str, body: str = None,
                        link: str = None, type: str = 'info') -> None:
    """Insert a notification for a user (no dedup)."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO notifications (user_id, title, body, link, type) VALUES (%s,%s,%s,%s,%s)",
            (user_id, title, body, link, type)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def create_notification_safe(user_id: int, title: str, body: str = None,
                              link: str = None, type: str = 'info',
                              event_key: str = None) -> bool:
    """
    Insert a notification, deduplicating by (user_id, event_key).
    If event_key is None, falls back to plain INSERT.
    Returns True if inserted, False if duplicate skipped.
    """
    if not event_key:
        try:
            create_notification(user_id, title, body, link, type)
            return True
        except Exception:
            return False

    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            """INSERT IGNORE INTO notifications (user_id, title, body, link, type, event_key)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (user_id, title, body, link, type, event_key)
        )
        inserted = cur.rowcount > 0
        conn.commit()
        return inserted
    except Exception:
        if conn: conn.rollback()
        return False
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_user_notifications(user_id: int, limit: int = 50) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT * FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, limit))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def count_unread(user_id: int) -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=%s AND is_read=0",
            (user_id,)
        )
        row = cur.fetchone()
        return row[0] if row else 0
    finally:
        if cur: cur.close()
        if conn: conn.close()


def mark_read(notif_id: int, user_id: int) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE notifications SET is_read=1 WHERE notif_id=%s AND user_id=%s",
            (notif_id, user_id)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def mark_all_read(user_id: int) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE notifications SET is_read=1 WHERE user_id=%s AND is_read=0",
            (user_id,)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def delete_notification(notif_id: int, user_id: int) -> bool:
    """Hard-delete a single notification. Returns True if deleted."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "DELETE FROM notifications WHERE notif_id=%s AND user_id=%s",
            (notif_id, user_id)
        )
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    except Exception:
        if conn: conn.rollback()
        return False
    finally:
        if cur: cur.close()
        if conn: conn.close()


def delete_all_notifications(user_id: int) -> None:
    """Hard-delete all notifications for a user."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM notifications WHERE user_id=%s", (user_id,))
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()
