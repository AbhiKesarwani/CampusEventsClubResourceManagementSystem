# services/log_service.py
"""
Centralized activity logging.
All write operations call log_action() to record in activity_logs.
"""
from database import get_db_connection
import logging

logger = logging.getLogger(__name__)


def log_action(user_id: int, action: str, entity_type: str = None,
               entity_id: int = None, details: str = None):
    """Insert a row into activity_logs. Silently fails on error (never breaks main flow)."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            """INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details)
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, action, entity_type, entity_id, details)
        )
        conn.commit()
    except Exception as e:
        logger.warning("log_action failed: %s", e)
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_recent_activity(limit: int = 15, user_id: int = None) -> list[dict]:
    """Return recent activity log rows joined with user name.

    Pass `user_id` to scope to a single user's own activity (used by the
    profile page); omitted, returns system-wide activity (used by the
    admin dashboard).
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        if user_id is not None:
            cur.execute(
                """SELECT al.*, u.name AS user_name
                   FROM activity_logs al
                   LEFT JOIN users u ON al.user_id = u.user_id
                   WHERE al.user_id = %s
                   ORDER BY al.created_at DESC
                   LIMIT %s""",
                (user_id, limit)
            )
        else:
            cur.execute(
                """SELECT al.*, u.name AS user_name
                   FROM activity_logs al
                   LEFT JOIN users u ON al.user_id = u.user_id
                   ORDER BY al.created_at DESC
                   LIMIT %s""",
                (limit,)
            )
        return cur.fetchall()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
