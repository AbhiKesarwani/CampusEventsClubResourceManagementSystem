# services/resource_service.py
from database import get_db_connection


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
                   quantity: int, requested_by: int) -> int:
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
              (event_id, club_id, resource_id, quantity, requested_by)
            VALUES (%s,%s,%s,%s,%s)
        """, (event_id, club_id, resource_id, quantity, requested_by))
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
        cur.execute(
            "SELECT * FROM resource_requests WHERE request_id=%s AND status='Pending'",
            (request_id,)
        )
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
        cur  = conn.cursor()
        cur.execute(
            "UPDATE resource_requests SET status='Rejected', reviewed_by=%s, updated_at=NOW() WHERE request_id=%s",
            (reviewed_by, request_id)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()
