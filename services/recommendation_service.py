# services/recommendation_service.py
from database import get_db_connection


def get_recommendations(user_id: int, limit: int = 9) -> list[dict]:
    """
    Recommend upcoming events based on clubs the user has previously attended.
    Falls back to all upcoming events if no attendance history.
    Always fetches venue_name and first_image.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)

        # Find top 3 clubs the user attended
        cur.execute("""
            SELECT e.club_id, COUNT(1) AS cnt
            FROM attendance a
            JOIN events e ON a.event_id = e.event_id
            WHERE a.user_id = %s
            GROUP BY e.club_id
            ORDER BY cnt DESC
            LIMIT 3
        """, (user_id,))
        clubs = cur.fetchall()
        club_ids = [str(c['club_id']) for c in clubs]

        base_query = """
            SELECT e.*, c.club_name, v.venue_name,
                   (SELECT img_path FROM event_images
                    WHERE event_id = e.event_id LIMIT 1) AS first_image
            FROM events e
            LEFT JOIN clubs  c ON e.club_id  = c.club_id
            LEFT JOIN venues v ON e.venue_id = v.venue_id
            WHERE e.date >= CURDATE()
        """

        if club_ids:
            placeholders = ",".join(club_ids)
            cur.execute(
                f"{base_query} AND e.club_id IN ({placeholders}) ORDER BY e.date ASC LIMIT %s",
                (limit,)
            )
        else:
            cur.execute(f"{base_query} ORDER BY e.date ASC LIMIT %s", (limit,))

        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def log_view(user_id: int, event_id: int) -> None:
    """Record that a user viewed an event (for future recommendation tuning)."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO user_activity (user_id, event_id, interaction_type)
            VALUES (%s, %s, 'viewed')
            ON DUPLICATE KEY UPDATE created_at = NOW()
        """, (user_id, event_id))
        conn.commit()
    except Exception:
        if conn:
            try: conn.rollback()
            except Exception: pass
    finally:
        if cur: cur.close()
        if conn: conn.close()
