# services/connect_service.py
# Campus Connect — Messages, Announcements, AI History
# Reuses existing DB pool, notification_service, and users.

from database import get_db_connection
from services.notification_service import create_notification_safe
import logging

logger = logging.getLogger(__name__)


# ── RBAC — chat permission enforcement (defense in depth; never trust client) ──

def _get_users_brief(user_ids: list) -> dict:
    """Return {user_id: {'user_id','role','club_id'}} for the given ids."""
    if not user_ids:
        return {}
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        placeholders = ','.join(['%s'] * len(user_ids))
        cur.execute(
            f"SELECT user_id, role, club_id FROM users WHERE user_id IN ({placeholders})",
            tuple(user_ids)
        )
        return {r['user_id']: r for r in cur.fetchall()}
    finally:
        if cur: cur.close()
        if conn: conn.close()


def can_message(sender_id: int, receiver_id: int) -> bool:
    """
    Server-side RBAC for direct messaging (checked on every send, never only
    in the UI's contact picker):
    - Admin may message anyone.
    - A reply is always allowed once a conversation already exists (so
      coordinators can answer students outside their club, and students /
      coordinators can reply to admin DMs).
    - Student may INITIATE a chat only with a club coordinator.
    - Coordinator may INITIATE a chat only with a member of their own club.
    """
    if sender_id == receiver_id:
        return False
    users = _get_users_brief([sender_id, receiver_id])
    sender, receiver = users.get(sender_id), users.get(receiver_id)
    if not sender or not receiver:
        return False
    if sender['role'] == 'admin':
        return True
    if count_conversation(sender_id, receiver_id) > 0:
        return True
    if sender['role'] == 'student' and receiver['role'] == 'club_admin':
        return True
    if sender['role'] == 'club_admin' and receiver['role'] == 'student':
        from services.member_service import is_member
        return bool(sender['club_id'] and is_member(sender['club_id'], receiver_id))
    return False


# ══════════════════════════════════════════════════════════════
# MESSAGES
# ══════════════════════════════════════════════════════════════

def send_message(sender_id: int, receiver_id: int, body: str,
                 sender_name: str = None, notify: bool = True) -> int:
    """Insert a DM after RBAC validation. Returns new msg_id.

    Raises PermissionError if the sender is not allowed to message the
    receiver — enforced server-side regardless of what the UI shows.

    `notify=False` suppresses the generic "New Message" notification, used
    by escalate_to_coordinator() which sends its own distinct notification
    instead (never send two notifications for one event).
    """
    if not body or not body.strip():
        raise ValueError("Message body cannot be empty.")
    body = body.strip()[:5000]

    if not can_message(sender_id, receiver_id):
        raise PermissionError("You are not allowed to message this user.")

    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO cc_messages (sender_id, receiver_id, body) VALUES (%s,%s,%s)",
            (sender_id, receiver_id, body)
        )
        msg_id = cur.lastrowid
        # Un-archive / un-delete the conversation for both sides if it was hidden.
        for uid, other in ((sender_id, receiver_id), (receiver_id, sender_id)):
            cur.execute(
                """INSERT INTO cc_conversation_state (user_id, other_id, is_archived, is_deleted)
                   VALUES (%s, %s, 0, 0)
                   ON DUPLICATE KEY UPDATE is_archived = 0, is_deleted = 0""",
                (uid, other)
            )
        conn.commit()
        # Notify receiver (deduplicated per message)
        if notify:
            try:
                create_notification_safe(
                    user_id=receiver_id,
                    title=f'New message from {sender_name}' if sender_name else 'New Message',
                    body=body[:140],
                    link=f'/connect?tab=messages&with={sender_id}',
                    type='cc_message',
                    event_key=f'cc_msg_{msg_id}'
                )
            except Exception:
                pass
        return msg_id
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_conversation(user_a: int, user_b: int,
                     page: int = 1, per_page: int = 40) -> list[dict]:
    """Fetch paginated messages between two users, oldest first."""
    offset = (page - 1) * per_page
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT m.msg_id, m.sender_id, m.receiver_id, m.body,
                      m.is_read, m.created_at,
                      s.name AS sender_name
               FROM cc_messages m
               JOIN users s ON s.user_id = m.sender_id
               WHERE (m.sender_id=%s AND m.receiver_id=%s)
                  OR (m.sender_id=%s AND m.receiver_id=%s)
               ORDER BY m.created_at ASC
               LIMIT %s OFFSET %s""",
            (user_a, user_b, user_b, user_a, per_page, offset)
        )
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def count_conversation(user_a: int, user_b: int) -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            """SELECT COUNT(*) FROM cc_messages
               WHERE (sender_id=%s AND receiver_id=%s)
                  OR (sender_id=%s AND receiver_id=%s)""",
            (user_a, user_b, user_b, user_a)
        )
        return cur.fetchone()[0]
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_inbox(user_id: int, include_archived: bool = False) -> list[dict]:
    """
    Return the latest message per conversation partner, plus unread count.
    Excludes conversations the user archived or deleted (unless requested).
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            f"""SELECT partner_id, partner_name, partner_role,
                      latest_body, latest_at,
                      SUM(unread) AS unread_count,
                      IFNULL(cs.is_archived, 0) AS is_archived
               FROM (
                 SELECT
                   CASE WHEN m.sender_id=%s THEN m.receiver_id ELSE m.sender_id END AS partner_id,
                   CASE WHEN m.sender_id=%s THEN rv.name        ELSE sv.name        END AS partner_name,
                   CASE WHEN m.sender_id=%s THEN rv.role        ELSE sv.role        END AS partner_role,
                   m.body  AS latest_body,
                   m.created_at AS latest_at,
                   CASE WHEN m.receiver_id=%s AND m.is_read=0 THEN 1 ELSE 0 END AS unread,
                   ROW_NUMBER() OVER (
                     PARTITION BY CASE WHEN m.sender_id=%s THEN m.receiver_id ELSE m.sender_id END
                     ORDER BY m.created_at DESC
                   ) AS rn
                 FROM cc_messages m
                 JOIN users sv ON sv.user_id = m.sender_id
                 JOIN users rv ON rv.user_id = m.receiver_id
                 WHERE m.sender_id=%s OR m.receiver_id=%s
               ) sub
               LEFT JOIN cc_conversation_state cs
                      ON cs.user_id = %s AND cs.other_id = sub.partner_id
               WHERE rn = 1
                 AND IFNULL(cs.is_deleted, 0) = 0
                 {"" if include_archived else "AND IFNULL(cs.is_archived, 0) = 0"}
               GROUP BY partner_id, partner_name, partner_role, latest_body, latest_at, cs.is_archived
               ORDER BY latest_at DESC""",
            # 8 placeholders: %s #1-3 (sender_id checks in CASE),
            # #4 (receiver_id unread check), #5 (PARTITION BY CASE),
            # #6-7 (WHERE sender OR receiver), #8 (LEFT JOIN cs.user_id)
            (user_id,) * 8
        )
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def set_conversation_archived(user_id: int, other_id: int, archived: bool) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            """INSERT INTO cc_conversation_state (user_id, other_id, is_archived)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE is_archived = %s""",
            (user_id, other_id, 1 if archived else 0, 1 if archived else 0)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_all_conversations_admin(search: str = None, page: int = 1, per_page: int = 30) -> list[dict]:
    """Admin moderation view: every conversation pair in the system with its
    latest message, newest first."""
    offset = (page - 1) * per_page
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        having = ""
        params: list = []
        if search:
            having = "HAVING a_name LIKE %s OR b_name LIKE %s"
            like = f"%{search}%"
            params = [like, like]
        cur.execute(
            f"""SELECT LEAST(m.sender_id, m.receiver_id) AS a_id,
                      GREATEST(m.sender_id, m.receiver_id) AS b_id,
                      MAX(m.created_at) AS latest_at,
                      SUBSTRING_INDEX(GROUP_CONCAT(m.body ORDER BY m.created_at DESC), ',', 1) AS latest_body,
                      ua.name AS a_name, ub.name AS b_name
               FROM cc_messages m
               JOIN users ua ON ua.user_id = LEAST(m.sender_id, m.receiver_id)
               JOIN users ub ON ub.user_id = GREATEST(m.sender_id, m.receiver_id)
               GROUP BY a_id, b_id, ua.name, ub.name
               {having}
               ORDER BY latest_at DESC
               LIMIT %s OFFSET %s""",
            params + [per_page, offset]
        )
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def mark_messages_read(viewer_id: int, sender_id: int) -> None:
    """Mark all messages FROM sender TO viewer as read (with read-receipt timestamp)."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE cc_messages SET is_read=1, read_at=NOW() "
            "WHERE sender_id=%s AND receiver_id=%s AND is_read=0",
            (sender_id, viewer_id)
        )
        conn.commit()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def count_unread_messages(user_id: int) -> int:
    """Count all unread messages for a user."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM cc_messages WHERE receiver_id=%s AND is_read=0",
            (user_id,)
        )
        return cur.fetchone()[0]
    finally:
        if cur: cur.close()
        if conn: conn.close()


def delete_conversation(user_id: int, partner_id: int) -> None:
    """Soft-delete a conversation for THIS user only (hides it from their
    inbox); the other participant's view is unaffected."""
    set_conversation_state_deleted(user_id, partner_id, True)


def set_conversation_state_deleted(user_id: int, other_id: int, deleted: bool) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            """INSERT INTO cc_conversation_state (user_id, other_id, is_deleted)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE is_deleted = %s""",
            (user_id, other_id, 1 if deleted else 0, 1 if deleted else 0)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def search_contacts(query: str, current_user_id: int,
                    role: str, club_id: int | None) -> list[dict]:
    """
    Search users the current session can START a NEW conversation with.
    Kept consistent with can_message() so the UI never offers a contact the
    backend will then reject:
    - Admin: anyone.
    - Coordinator: members of their own club only.
    - Student: club coordinators only.
    (Replies to an existing conversation are always allowed regardless of
    this list — see can_message().)
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        like = f"%{query}%"

        if role == 'admin':
            cur.execute(
                "SELECT user_id, name, email, role FROM users "
                "WHERE user_id != %s AND (name LIKE %s OR email LIKE %s) "
                "ORDER BY role, name LIMIT 20",
                (current_user_id, like, like)
            )
        elif role == 'club_admin':
            if not club_id:
                return []
            cur.execute(
                """SELECT u.user_id, u.name, u.email, u.role
                   FROM club_members cm
                   JOIN users u ON u.user_id = cm.user_id
                   WHERE cm.club_id = %s AND u.user_id != %s
                     AND (u.name LIKE %s OR u.email LIKE %s)
                   ORDER BY u.name LIMIT 20""",
                (club_id, current_user_id, like, like)
            )
        else:
            # Student: can only initiate with club coordinators.
            cur.execute(
                """SELECT DISTINCT u.user_id, u.name, u.email, u.role, c.club_name
                   FROM users u
                   JOIN clubs c ON c.coordinator_id = u.user_id
                   WHERE u.user_id != %s
                     AND (u.name LIKE %s OR u.email LIKE %s OR c.club_name LIKE %s)
                   ORDER BY c.club_name LIMIT 20""",
                (current_user_id, like, like, like)
            )
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


# ══════════════════════════════════════════════════════════════
# ANNOUNCEMENTS
# ══════════════════════════════════════════════════════════════

VALID_ANNOUNCEMENT_TARGETS = {'everyone', 'students', 'coordinators', 'club', 'user'}


def create_announcement(author_id: int, author_role: str, author_club_id: int | None,
                        target_type: str, target_id: int | None,
                        title: str, body: str,
                        pinned: bool = False) -> int:
    """
    Create an announcement and fan-out notifications.
    RBAC is enforced here (never trust the route/UI alone):
    - student: never allowed to broadcast.
    - club_admin: target_type must be 'club', targeting ONLY their own club.
    - admin: any target_type.
    Returns new ann_id.
    """
    if not title.strip() or not body.strip():
        raise ValueError("Title and body are required.")
    if target_type not in VALID_ANNOUNCEMENT_TARGETS:
        raise ValueError("Invalid target type.")

    if author_role == 'student':
        raise PermissionError("Students cannot post announcements.")
    if author_role == 'club_admin':
        if target_type == 'club':
            if not author_club_id or (target_id and int(target_id) != int(author_club_id)):
                raise PermissionError("Coordinators may only broadcast to their own club.")
            target_id = author_club_id
        elif target_type == 'students':
            target_id = None
        else:
            raise PermissionError("Coordinators may only broadcast to their own club or all students.")
    elif author_role != 'admin':
        raise PermissionError("Access denied.")

    if target_type in ('club', 'user') and not target_id:
        raise ValueError("target_id is required for club/user announcements.")

    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            """INSERT INTO cc_announcements
               (author_id, target_type, target_id, title, body, is_pinned)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (author_id, target_type, target_id,
             title.strip(), body.strip(), 1 if pinned else 0)
        )
        conn.commit()
        ann_id = cur.lastrowid

        # Fan-out notifications
        _fanout_announcement_notifications(
            conn, ann_id, author_id, target_type, target_id, title, body
        )
        return ann_id
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def _fanout_announcement_notifications(conn, ann_id: int, author_id: int,
                                        target_type: str, target_id: int | None,
                                        title: str, body: str) -> None:
    """Send notifications to all recipients of an announcement."""
    cur2 = conn.cursor(dictionary=True)
    try:
        if target_type == 'everyone':
            cur2.execute("SELECT user_id FROM users WHERE user_id != %s", (author_id,))
        elif target_type == 'students':
            cur2.execute("SELECT user_id FROM users WHERE role='student' AND user_id!=%s", (author_id,))
        elif target_type == 'coordinators':
            cur2.execute("SELECT user_id FROM users WHERE role='club_admin' AND user_id!=%s", (author_id,))
        elif target_type == 'club' and target_id:
            # Club membership lives in club_members (students) + clubs.coordinator_id,
            # NOT users.club_id (which is only meaningful for coordinators).
            cur2.execute(
                """SELECT user_id FROM club_members WHERE club_id=%s AND user_id!=%s
                   UNION
                   SELECT coordinator_id AS user_id FROM clubs
                   WHERE club_id=%s AND coordinator_id IS NOT NULL AND coordinator_id!=%s""",
                (target_id, author_id, target_id, author_id)
            )
        elif target_type == 'user' and target_id:
            cur2.execute("SELECT user_id FROM users WHERE user_id=%s", (target_id,))
        else:
            return

        recipients = cur2.fetchall()
        for r in recipients:
            try:
                create_notification_safe(
                    user_id=r['user_id'],
                    title=f'New announcement: {title}',
                    body=body[:200],
                    link=f'/connect?tab=announcements&ann={ann_id}',
                    type='cc_announcement',
                    event_key=f'cc_ann_{ann_id}_{r["user_id"]}'
                )
            except Exception:
                pass
    finally:
        cur2.close()


def get_announcements_for_user(user_id: int, role: str,
                                club_id: int | None,
                                page: int = 1, per_page: int = 20) -> list[dict]:
    """
    Fetch announcements visible to the given user:
    - everyone: all roles see it
    - students: only role=student
    - coordinators: only role=club_admin
    - club: users with that club_id
    - user: that specific user_id
    Pinned first, then newest.
    """
    offset = (page - 1) * per_page
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)

        if role == 'admin':
            # Admin sees everything
            cur.execute(
                """SELECT a.*, u.name AS author_name, u.role AS author_role
                   FROM cc_announcements a JOIN users u ON a.author_id=u.user_id
                   ORDER BY a.is_pinned DESC, a.created_at DESC
                   LIMIT %s OFFSET %s""",
                (per_page, offset)
            )
        else:
            cur.execute(
                """SELECT a.*, u.name AS author_name, u.role AS author_role
                   FROM cc_announcements a JOIN users u ON a.author_id=u.user_id
                   WHERE a.author_id=%s
                      OR a.target_type='everyone'
                      OR (a.target_type='students' AND %s='student')
                      OR (a.target_type='coordinators' AND %s='club_admin')
                      OR (a.target_type='club' AND a.target_id IN (
                            SELECT club_id FROM club_members WHERE user_id=%s
                            UNION SELECT %s))
                      OR (a.target_type='user' AND a.target_id=%s)
                   ORDER BY a.is_pinned DESC, a.created_at DESC
                   LIMIT %s OFFSET %s""",
                (user_id, role, role, user_id, club_id, user_id, per_page, offset)
            )
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def count_announcements_for_user(user_id: int, role: str, club_id: int | None) -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        if role == 'admin':
            cur.execute("SELECT COUNT(*) FROM cc_announcements")
        else:
            cur.execute(
                """SELECT COUNT(*) FROM cc_announcements
                   WHERE author_id=%s
                      OR target_type='everyone'
                      OR (target_type='students' AND %s='student')
                      OR (target_type='coordinators' AND %s='club_admin')
                      OR (target_type='club' AND target_id IN (
                            SELECT club_id FROM club_members WHERE user_id=%s
                            UNION SELECT %s))
                      OR (target_type='user' AND target_id=%s)""",
                (user_id, role, role, user_id, club_id, user_id)
            )
        return cur.fetchone()[0]
    finally:
        if cur: cur.close()
        if conn: conn.close()


def toggle_pin_announcement(ann_id: int, requester_id: int, requester_role: str) -> None:
    """Pin/unpin an announcement. Admin (moderation) or the original author only."""
    ann = get_announcement_by_id(ann_id)
    if not ann:
        raise ValueError("Announcement not found.")
    if requester_role != 'admin' and ann['author_id'] != requester_id:
        raise PermissionError("You cannot modify this announcement.")
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE cc_announcements SET is_pinned = 1 - is_pinned WHERE ann_id=%s",
            (ann_id,)
        )
        conn.commit()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def delete_announcement(ann_id: int, requester_id: int, requester_role: str) -> None:
    """Admin can delete any announcement (moderation); authors can delete their own."""
    ann = get_announcement_by_id(ann_id)
    if not ann:
        raise ValueError("Announcement not found.")
    if requester_role != 'admin' and ann['author_id'] != requester_id:
        raise PermissionError("You cannot delete this announcement.")
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM cc_announcements WHERE ann_id=%s", (ann_id,))
        conn.commit()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_announcement_by_id(ann_id: int) -> dict | None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT a.*, u.name AS author_name FROM cc_announcements a "
            "JOIN users u ON a.author_id=u.user_id WHERE a.ann_id=%s",
            (ann_id,)
        )
        return cur.fetchone()
    finally:
        if cur: cur.close()
        if conn: conn.close()


# ══════════════════════════════════════════════════════════════
# AI HISTORY
# ══════════════════════════════════════════════════════════════

def save_ai_message(user_id: int, role: str, content: str,
                    source: str = 'ai') -> None:
    """Append a message to the user's AI conversation history."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO cc_ai_history (user_id, role, content, source) VALUES (%s,%s,%s,%s)",
            (user_id, role, content, source)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_ai_history(user_id: int, limit: int = 20) -> list[dict]:
    """Fetch recent AI history for context, oldest first."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT role, content, source, created_at
               FROM cc_ai_history
               WHERE user_id=%s
               ORDER BY created_at DESC LIMIT %s""",
            (user_id, limit)
        )
        rows = cur.fetchall()
        return list(reversed(rows))  # oldest first
    finally:
        if cur: cur.close()
        if conn: conn.close()


def clear_ai_history(user_id: int) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM cc_ai_history WHERE user_id=%s", (user_id,))
        conn.commit()
    finally:
        if cur: cur.close()
        if conn: conn.close()


# ══════════════════════════════════════════════════════════════
# ESCALATION
# ══════════════════════════════════════════════════════════════

def escalate_to_coordinator(user_id: int, user_name: str, question: str,
                            coordinator_id: int | None = None,
                            club_id: int | None = None) -> bool:
    """
    Create a DM from a student to a club coordinator with the escalated
    question the AI couldn't confidently answer.

    Resolution order for the target coordinator:
      1. Explicit `coordinator_id` (student picked one from the UI).
      2. Coordinator of `club_id` (if the question was already club-scoped).
      3. Any available coordinator (last-resort fallback).

    Returns True if sent, False if no coordinator could be found.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)

        coord_id = None
        if coordinator_id:
            cur.execute(
                "SELECT user_id AS coordinator_id FROM users WHERE user_id=%s AND role='club_admin'",
                (coordinator_id,)
            )
            row = cur.fetchone()
            coord_id = row['coordinator_id'] if row else None

        if not coord_id and club_id:
            cur.execute(
                "SELECT coordinator_id FROM clubs WHERE club_id=%s AND coordinator_id IS NOT NULL",
                (club_id,)
            )
            row = cur.fetchone()
            coord_id = row['coordinator_id'] if row else None

        if not coord_id:
            cur.execute(
                "SELECT user_id AS coordinator_id FROM users WHERE role='club_admin' LIMIT 1"
            )
            row = cur.fetchone()
            coord_id = row['coordinator_id'] if row else None

        if not coord_id:
            return False

        body = f"[AI Escalation] {user_name} asked: \"{question.strip()}\"\n\nThe AI assistant couldn't confidently answer this. Could you help?"
        msg_id = send_message(user_id, coord_id, body, sender_name=user_name, notify=False)
        # Single distinct notification for this event (no generic "new message" dup).
        create_notification_safe(
            user_id=coord_id,
            title=f'AI Escalation from {user_name}',
            body=question[:140],
            link=f'/connect?tab=messages&with={user_id}',
            type='cc_escalation',
            event_key=f'cc_escalate_{msg_id}'
        )
        return True
    except Exception as e:
        logger.warning("Escalation failed: %s", e)
        return False
    finally:
        if cur: cur.close()
        if conn: conn.close()
