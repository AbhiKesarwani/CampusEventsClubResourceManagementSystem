# services/resource_service.py
from datetime import datetime
from database import get_db_connection


def release_expired_allocations() -> int:
    """
    Check all Approved resource_requests where the associated event's
    end_time + date have passed. Mark them Completed and reduce event_resources.
    Called on dashboard / resource page loads — no cron needed.
    Returns number of requests auto-released.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)

        # Find approved requests whose event has already ended
        cur.execute("""
            SELECT rr.request_id, rr.resource_id, rr.quantity,
                   rr.event_id, rr.requested_by,
                   r.resource_name,
                   e.title AS event_title, e.date, e.end_time
            FROM resource_requests rr
            JOIN events    e ON e.event_id     = rr.event_id
            JOIN resources r ON r.resource_id  = rr.resource_id
            WHERE rr.status = 'Approved'
              AND rr.auto_released = 0
              AND e.date IS NOT NULL
              AND e.end_time IS NOT NULL
              AND TIMESTAMP(e.date, e.end_time) < NOW()
        """)
        expired = cur.fetchall()
        if not expired:
            return 0

        cur2 = conn.cursor()
        for req in expired:
            # Mark request completed
            cur2.execute("""
                UPDATE resource_requests
                SET status='Completed', auto_released=1, updated_at=NOW()
                WHERE request_id=%s
            """, (req['request_id'],))

            # Reduce event_resources (remove allocation)
            cur2.execute("""
                UPDATE event_resources
                SET quantity = GREATEST(0, quantity - %s)
                WHERE event_id=%s AND resource_id=%s
            """, (req['quantity'], req['event_id'], req['resource_id']))

            # Clean up zero-quantity rows
            cur2.execute("""
                DELETE FROM event_resources
                WHERE event_id=%s AND resource_id=%s AND quantity <= 0
            """, (req['event_id'], req['resource_id']))

        conn.commit()

        # Fire deduped notifications (after commit)
        try:
            from services.notification_service import create_notification_safe
            for req in expired:
                create_notification_safe(
                    user_id=req['requested_by'],
                    title='Resource Automatically Returned',
                    body=(f"{req['quantity']}x {req['resource_name']} has been automatically "
                          f"returned after '{req['event_title']}' ended."),
                    link='/resources/my-requests',
                    type='info',
                    event_key=f"auto_release_{req['request_id']}"
                )
        except Exception:
            pass  # Never let notification failure break the release

        return len(expired)
    except Exception:
        if conn: conn.rollback()
        return 0
    finally:
        if cur: cur.close()
        if conn: conn.close()



# ── Resources ─────────────────────────────────────────────────────────────────


def get_all_resources() -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT r.resource_id, r.resource_name, r.total_quantity, r.description,
                   IFNULL(SUM(CASE WHEN rr.status='Approved' THEN rr.quantity ELSE 0 END), 0) AS allocated,
                   r.total_quantity - IFNULL(SUM(CASE WHEN rr.status='Approved' THEN rr.quantity ELSE 0 END), 0) AS available
            FROM resources r
            LEFT JOIN resource_requests rr ON r.resource_id = rr.resource_id
            GROUP BY r.resource_id, r.resource_name, r.total_quantity, r.description
            ORDER BY r.resource_name
        """)
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_resource_by_id(resource_id: int) -> dict | None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM resources WHERE resource_id = %s", (resource_id,)
        )
        return cur.fetchone()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def create_resource(resource_name: str, total_quantity: int, description: str = None) -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO resources (resource_name, total_quantity, description) VALUES (%s,%s,%s)",
            (resource_name, total_quantity, description)
        )
        conn.commit()
        return cur.lastrowid
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def update_resource(resource_id: int, resource_name: str, total_quantity: int, description: str = None) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE resources SET resource_name=%s, total_quantity=%s, description=%s WHERE resource_id=%s",
            (resource_name, total_quantity, description, resource_id)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def delete_resource(resource_id: int) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM resources WHERE resource_id = %s", (resource_id,))
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def count_resources() -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM resources")
        return cur.fetchone()[0]
    finally:
        if cur: cur.close()
        if conn: conn.close()


# ── Resource Requests ─────────────────────────────────────────────────────────

def get_all_requests(status: str = None) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        query = """
            SELECT rr.*, r.resource_name, e.title AS event_title,
                   c.club_name, u.name AS requested_by_name,
                   rev.name AS reviewed_by_name
            FROM resource_requests rr
            JOIN resources r ON r.resource_id = rr.resource_id
            JOIN events    e ON e.event_id     = rr.event_id
            JOIN clubs     c ON c.club_id      = rr.club_id
            JOIN users     u ON u.user_id      = rr.requested_by
            LEFT JOIN users rev ON rev.user_id = rr.reviewed_by
        """
        params = []
        if status:
            query += " WHERE rr.status = %s"
            params.append(status)
        query += " ORDER BY rr.created_at DESC"
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_requests_for_club(club_id: int) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT rr.*, r.resource_name, e.title AS event_title,
                   rev.name AS reviewed_by_name
            FROM resource_requests rr
            JOIN resources r ON r.resource_id = rr.resource_id
            JOIN events    e ON e.event_id     = rr.event_id
            LEFT JOIN users rev ON rev.user_id = rr.reviewed_by
            WHERE rr.club_id = %s
            ORDER BY rr.created_at DESC
        """, (club_id,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def count_pending_requests() -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM resource_requests WHERE status='Pending'")
        return cur.fetchone()[0]
    finally:
        if cur: cur.close()
        if conn: conn.close()


def create_request(event_id: int, club_id: int, resource_id: int,
                   quantity: int, requested_by: int, reason: str = None,
                   required_date=None, req_start_time=None,
                   req_end_time=None, purpose: str = None,
                   remarks: str = None) -> int:
    """Submit a resource request. Raises ValueError on over-allocation."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        # Check available stock
        cur.execute("""
            SELECT r.total_quantity,
                   IFNULL(SUM(CASE WHEN rr.status='Approved' THEN rr.quantity ELSE 0 END), 0) AS allocated
            FROM resources r
            LEFT JOIN resource_requests rr ON r.resource_id = rr.resource_id
            WHERE r.resource_id = %s
            GROUP BY r.resource_id
        """, (resource_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Resource not found.")
        available = row['total_quantity'] - row['allocated']
        if quantity > available:
            raise ValueError(f"Only {available} unit(s) available.")

        cur2 = conn.cursor()
        cur2.execute("""
            INSERT INTO resource_requests
              (event_id, club_id, resource_id, quantity, requested_by,
               reason, required_date, req_start_time, req_end_time, purpose, remarks)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (event_id, club_id, resource_id, quantity, requested_by,
              reason, required_date, req_start_time, req_end_time, purpose, remarks))
        conn.commit()
        return cur2.lastrowid
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def approve_request(request_id: int, reviewed_by: int) -> None:
    """Approve a request and add to event_resources."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT rr.*, r.resource_name, e.title AS event_title
            FROM resource_requests rr
            JOIN resources r ON r.resource_id = rr.resource_id
            JOIN events    e ON e.event_id     = rr.event_id
            WHERE rr.request_id=%s AND rr.status='Pending'
        """, (request_id,))
        req = cur.fetchone()
        if not req:
            raise ValueError("Request not found or already reviewed.")

        # Check available stock again before approving
        cur.execute("""
            SELECT r.total_quantity,
                   IFNULL(SUM(CASE WHEN rr.status='Approved' THEN rr.quantity ELSE 0 END), 0) AS allocated
            FROM resources r
            LEFT JOIN resource_requests rr ON r.resource_id = rr.resource_id
            WHERE r.resource_id = %s
            GROUP BY r.resource_id
        """, (req['resource_id'],))
        stock = cur.fetchone()
        available = stock['total_quantity'] - stock['allocated']
        if req['quantity'] > available:
            raise ValueError(f"Cannot approve: only {available} unit(s) available now.")

        cur2 = conn.cursor()
        cur2.execute(
            "UPDATE resource_requests SET status='Approved', reviewed_by=%s, updated_at=NOW() WHERE request_id=%s",
            (reviewed_by, request_id)
        )
        # Upsert into event_resources
        cur2.execute("""
            INSERT INTO event_resources (event_id, resource_id, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)
        """, (req['event_id'], req['resource_id'], req['quantity']))
        conn.commit()

        # Fire notification to requesting coordinator
        try:
            from services.notification_service import create_notification
            create_notification(
                user_id=req['requested_by'],
                title='Resource Request Approved',
                body=f"{req['quantity']}x {req['resource_name']} approved for '{req['event_title']}'.",
                link='/resources/requests',
                type='resource_approved'
            )
        except Exception:
            pass  # Never let notification failure break the approval
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def reject_request(request_id: int, reviewed_by: int) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        # Fetch request details for notification
        cur.execute("""
            SELECT rr.*, r.resource_name, e.title AS event_title
            FROM resource_requests rr
            JOIN resources r ON r.resource_id = rr.resource_id
            JOIN events    e ON e.event_id     = rr.event_id
            WHERE rr.request_id = %s
        """, (request_id,))
        req = cur.fetchone()

        cur2 = conn.cursor()
        cur2.execute(
            "UPDATE resource_requests SET status='Rejected', reviewed_by=%s, updated_at=NOW() WHERE request_id=%s",
            (reviewed_by, request_id)
        )
        conn.commit()

        # Fire notification to requesting coordinator
        if req:
            try:
                from services.notification_service import create_notification
                create_notification(
                    user_id=req['requested_by'],
                    title='Resource Request Rejected',
                    body=f"{req['quantity']}x {req['resource_name']} for '{req['event_title']}' was not approved.",
                    link='/resources/requests',
                    type='resource_rejected'
                )
            except Exception:
                pass
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()
