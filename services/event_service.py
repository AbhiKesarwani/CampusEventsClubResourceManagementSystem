# services/event_service.py
from database import get_db_connection


# ── List / Fetch ─────────────────────────────────────────────────────────────

def get_all_events(club_id=None, venue_id=None, date_from=None,
                   date_to=None, upcoming=False, past=False,
                   search=None, status=None,
                   page=None, per_page=12) -> list[dict]:
    """Fetch events with optional filters, search, and pagination."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        query = """
            SELECT e.*, c.club_name, v.venue_name,
                   (SELECT img_path FROM event_images
                    WHERE event_id = e.event_id LIMIT 1) AS first_image
            FROM events e
            LEFT JOIN clubs  c ON e.club_id  = c.club_id
            LEFT JOIN venues v ON e.venue_id = v.venue_id
            WHERE 1=1
        """
        params = []
        if club_id:
            query += " AND e.club_id = %s"
            params.append(club_id)
        if venue_id:
            query += " AND e.venue_id = %s"
            params.append(venue_id)
        if date_from:
            query += " AND e.date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND e.date <= %s"
            params.append(date_to)
        # status param takes priority over individual upcoming/past flags
        if status == 'upcoming':
            query += " AND e.date > CURDATE()"
        elif status == 'ongoing':
            query += " AND e.date = CURDATE()"
        elif status == 'past':
            query += " AND e.date < CURDATE()"
        else:
            # legacy flag support
            if upcoming:
                query += " AND e.date >= CURDATE()"
            if past:
                query += " AND e.date < CURDATE()"
        if search:
            query += " AND e.title LIKE %s"
            params.append(f"%{search}%")
        query += " ORDER BY e.created_at DESC, e.date DESC"
        if page is not None:
            offset = (page - 1) * per_page
            query += " LIMIT %s OFFSET %s"
            params.extend([per_page, offset])
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def count_all_events(club_id=None, venue_id=None, date_from=None,
                     date_to=None, upcoming=False, past=False,
                     search=None, status=None) -> int:
    """Count events matching filters (for pagination)."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        query = "SELECT COUNT(*) FROM events e WHERE 1=1"
        params = []
        if club_id:
            query += " AND e.club_id = %s"
            params.append(club_id)
        if venue_id:
            query += " AND e.venue_id = %s"
            params.append(venue_id)
        if date_from:
            query += " AND e.date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND e.date <= %s"
            params.append(date_to)
        if status == 'upcoming':
            query += " AND e.date > CURDATE()"
        elif status == 'ongoing':
            query += " AND e.date = CURDATE()"
        elif status == 'past':
            query += " AND e.date < CURDATE()"
        else:
            if upcoming:
                query += " AND e.date >= CURDATE()"
            if past:
                query += " AND e.date < CURDATE()"
        if search:
            query += " AND e.title LIKE %s"
            params.append(f"%{search}%")
        cur.execute(query, params)
        row = cur.fetchone()
        return row[0] if row else 0
    finally:
        if cur: cur.close()
        if conn: conn.close()



def get_event_by_id(event_id: int) -> dict | None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT e.*, c.club_name, c.description AS club_description,
                   v.venue_name
            FROM events e
            LEFT JOIN clubs  c ON e.club_id  = c.club_id
            LEFT JOIN venues v ON e.venue_id = v.venue_id
            WHERE e.event_id = %s
        """, (event_id,))
        return cur.fetchone()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_event_images(event_id: int) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM event_images WHERE event_id = %s ORDER BY img_id ASC", (event_id,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_upcoming_events(limit: int = 10, club_id: int = None) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        where = "WHERE e.date >= CURDATE()"
        params = []
        if club_id:
            where += " AND e.club_id = %s"
            params.append(club_id)
        params.append(limit)
        cur.execute(f"""
            SELECT e.*, c.club_name, v.venue_name,
                   (SELECT img_path FROM event_images WHERE event_id = e.event_id LIMIT 1) AS first_image
            FROM events e
            LEFT JOIN clubs  c ON e.club_id  = c.club_id
            LEFT JOIN venues v ON e.venue_id = v.venue_id
            {where}
            ORDER BY e.date ASC
            LIMIT %s
        """, params)
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_related_events(event_id: int, club_id: int, limit: int = 3) -> list[dict]:
    """Get other events from the same club (excluding current event)."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT e.*, c.club_name, v.venue_name,
                   (SELECT img_path FROM event_images WHERE event_id = e.event_id LIMIT 1) AS first_image
            FROM events e
            LEFT JOIN clubs  c ON e.club_id  = c.club_id
            LEFT JOIN venues v ON e.venue_id = v.venue_id
            WHERE e.club_id = %s AND e.event_id != %s
            ORDER BY e.date DESC
            LIMIT %s
        """, (club_id, event_id, limit))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_events_for_club(club_id: int) -> list[dict]:
    return get_all_events(club_id=club_id)


# ── Create / Update / Delete ─────────────────────────────────────────────────

def create_event(club_id, title, description, event_lead, contact_no,
                 venue_id, date, start_time, end_time, registration_link, created_by) -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        # Venue conflict check
        cur.execute("""
            SELECT event_id FROM events
            WHERE venue_id=%s AND date=%s
              AND (
                    (start_time <= %s AND end_time > %s)
                 OR (start_time < %s AND end_time >= %s)
                 OR (start_time >= %s AND end_time <= %s)
              )
        """, (venue_id, date, start_time, start_time,
              end_time, end_time,
              start_time, end_time))
        if cur.fetchone():
            raise ValueError("Venue is already booked for this date/time slot.")

        cur2 = conn.cursor()
        cur2.execute("""
            INSERT INTO events
              (club_id, title, description, event_lead, contact_no,
               venue_id, date, start_time, end_time, registration_link, created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (club_id, title, description, event_lead, contact_no,
              venue_id, date, start_time, end_time, registration_link, created_by))
        conn.commit()
        return cur2.lastrowid
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def update_event(event_id, club_id, title, description, event_lead, contact_no,
                 venue_id, date, start_time, end_time, registration_link) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("""
            UPDATE events
            SET club_id=%s, title=%s, description=%s, event_lead=%s, contact_no=%s,
                venue_id=%s, date=%s, start_time=%s, end_time=%s, registration_link=%s
            WHERE event_id=%s
        """, (club_id, title, description, event_lead, contact_no,
              venue_id, date, start_time, end_time, registration_link, event_id))
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def delete_event(event_id: int) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM events WHERE event_id = %s", (event_id,))
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


# ── Images ────────────────────────────────────────────────────────────────────

def add_event_image(event_id: int, img_path: str) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("INSERT INTO event_images (event_id, img_path) VALUES (%s,%s)", (event_id, img_path))
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def delete_event_image(img_id: int, event_id: int) -> str | None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT img_path FROM event_images WHERE img_id=%s AND event_id=%s", (img_id, event_id))
        row = cur.fetchone()
        if row:
            cur.execute("DELETE FROM event_images WHERE img_id=%s", (img_id,))
            conn.commit()
            return row['img_path']
        return None
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


# ── Stats ─────────────────────────────────────────────────────────────────────

def count_events() -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM events")
        return cur.fetchone()[0]
    finally:
        if cur: cur.close()
        if conn: conn.close()
