# services/resource_service.py
from database import get_db_connection


def release_expired_allocations() -> int:
    """
    Check all Approved resource_requests where EITHER:
      (a) the explicit return_date + return_time has passed, OR
      (b) the associated event's end_time + date has passed.
    Whichever comes first triggers the release.
    Mark them Completed, restore resource quantity, and notify.
    Called on dashboard / resource page loads — no cron needed.
    Returns number of requests auto-released.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)

        # Find approved requests where return window has passed
        cur.execute("""
            SELECT rr.request_id, rr.resource_id, rr.quantity,
                   rr.event_id, rr.requested_by,
                   rr.return_date, rr.return_time,
                   r.resource_name,
                   e.title AS event_title, e.date, e.end_time
            FROM resource_requests rr
            JOIN events    e ON e.event_id     = rr.event_id
            JOIN resources r ON r.resource_id  = rr.resource_id
            WHERE rr.status = 'Approved'
              AND rr.auto_released = 0
              AND (
                -- Explicit return datetime has passed
                (rr.return_date IS NOT NULL AND rr.return_time IS NOT NULL
                 AND TIMESTAMP(rr.return_date, rr.return_time) < NOW())
                OR
                -- Event end time has passed (fallback)
                (e.date IS NOT NULL AND e.end_time IS NOT NULL
                 AND TIMESTAMP(e.date, e.end_time) < NOW())
              )
        """)
        expired = cur.fetchall()
        if not expired:
            return 0

        ids = [req['request_id'] for req in expired]
        placeholders = ','.join(['%s'] * len(ids))

        cur2 = conn.cursor()

        # Mark all expired requests completed in one statement.
        cur2.execute(
            f"""UPDATE resource_requests
                SET status='Completed', auto_released=1, updated_at=NOW()
                WHERE request_id IN ({placeholders})""",
            ids
        )

        # Restore resource quantities in one statement (grouped per resource,
        # in case several expired requests share the same resource).
        cur2.execute(
            f"""UPDATE resources r
                JOIN (
                    SELECT resource_id, SUM(quantity) AS qty
                    FROM resource_requests
                    WHERE request_id IN ({placeholders})
                    GROUP BY resource_id
                ) t ON t.resource_id = r.resource_id
                SET r.total_quantity = r.total_quantity + t.qty""",
            ids
        )

        # Reduce event_resources allocations in one statement (grouped per
        # event+resource pair).
        cur2.execute(
            f"""UPDATE event_resources er
                JOIN (
                    SELECT event_id, resource_id, SUM(quantity) AS qty
                    FROM resource_requests
                    WHERE request_id IN ({placeholders})
                    GROUP BY event_id, resource_id
                ) t ON t.event_id = er.event_id AND t.resource_id = er.resource_id
                SET er.quantity = GREATEST(0, er.quantity - t.qty)""",
            ids
        )

        # Clean up any allocation rows that dropped to zero.
        cur2.execute("DELETE FROM event_resources WHERE quantity <= 0")

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



# ── Request Lookup ─────────────────────────────────────────────────────────────

def get_request_by_id(request_id: int) -> dict | None:
    """Fetch a single resource request with resource_name and event_title."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT rr.*, r.resource_name, e.title AS event_title
            FROM resource_requests rr
            JOIN resources r ON r.resource_id = rr.resource_id
            JOIN events    e ON e.event_id     = rr.event_id
            WHERE rr.request_id = %s
        """, (request_id,))
        return cur.fetchone()
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


def get_resource_requests_for_club(club_id: int) -> list[dict]:
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
                   remarks: str = None,
                   return_date=None, return_time=None) -> int:
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
               reason, required_date, req_start_time, req_end_time,
               purpose, remarks, return_date, return_time)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (event_id, club_id, resource_id, quantity, requested_by,
               reason, required_date, req_start_time, req_end_time,
               purpose, remarks, return_date, return_time))
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
        # Note: the caller (routes/resources.py::approve) sends the requester
        # notification via create_notification_safe() with dedup — do not
        # duplicate that here.
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
        # Fetch request details (route layer uses this for its own notification)
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
        # Note: the caller (routes/resources.py::reject) sends the requester
        # notification via create_notification_safe() with dedup — do not
        # duplicate that here.
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()
