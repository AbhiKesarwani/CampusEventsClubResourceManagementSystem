# services/recommendation_service.py
from database import get_db_connection


def get_recommendations(user_id: int, limit: int = 9) -> list[dict]:
    """
    Weighted recommendation engine.
    Scoring:
      +50  clubs the student has previously attended
      +30  clubs the student belongs to (membership)
      +20  same category as events already attended
      +15  popularity (attendance count, capped contribution)
      +10  upcoming (date >= today)
    Excludes: already-attended events, past events.
    Returns events sorted by score desc, with a 'reason' field.
    """
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)

        # ── 1. Clubs student attended ──────────────────────────────
        cur.execute("""
            SELECT e.club_id, COUNT(1) AS cnt
            FROM attendance a
            JOIN events e ON a.event_id = e.event_id
            WHERE a.user_id = %s
            GROUP BY e.club_id
        """, (user_id,))
        attended_clubs = {r['club_id']: r['cnt'] for r in cur.fetchall()}

        # ── 2. Clubs student is a member of ───────────────────────
        cur.execute("""
            SELECT DISTINCT club_id FROM club_members
            WHERE user_id = %s
        """, (user_id,))
        member_clubs = {r['club_id'] for r in cur.fetchall()}

        # ── 3. Categories of events student attended ───────────────
        cur.execute("""
            SELECT DISTINCT ev.category
            FROM attendance a
            JOIN events ev ON a.event_id = ev.event_id
            WHERE a.user_id = %s AND ev.category IS NOT NULL AND ev.category != ''
        """, (user_id,))
        attended_categories = {r['category'] for r in cur.fetchall()}

        # ── 4. Events already attended by student ─────────────────
        cur.execute("""
            SELECT event_id FROM attendance WHERE user_id = %s
        """, (user_id,))
        attended_event_ids = {r['event_id'] for r in cur.fetchall()}

        # ── 5. Fetch candidate upcoming events ────────────────────
        cur.execute("""
            SELECT e.event_id, e.title, e.date, e.start_time, e.end_time,
                   e.description, e.registration_link, e.category,
                   e.club_id, e.venue_id,
                   c.club_name,
                   v.venue_name,
                   u.name  AS coordinator_name,
                   (SELECT img_path FROM event_images
                    WHERE event_id = e.event_id LIMIT 1) AS first_image,
                   (SELECT COUNT(*) FROM attendance a2
                    WHERE a2.event_id = e.event_id)      AS attendance_count
            FROM events e
            LEFT JOIN clubs  c ON e.club_id  = c.club_id
            LEFT JOIN venues v ON e.venue_id = v.venue_id
            LEFT JOIN users  u ON c.coordinator_id = u.user_id
            WHERE e.date >= CURDATE()
            ORDER BY e.date ASC
            LIMIT 60
        """)
        candidates = cur.fetchall()

        # ── 6. Score each candidate ────────────────────────────────
        scored = []
        for ev in candidates:
            if ev['event_id'] in attended_event_ids:
                continue  # never recommend already-attended

            score  = 0
            reasons = []

            club_id = ev['club_id']

            # +50 attended club
            if club_id in attended_clubs:
                score += 50
                reasons.append(f"Because you attended {ev['club_name']}")

            # +30 member club
            if club_id in member_clubs and club_id not in attended_clubs:
                score += 30
                reasons.append(f"Your club: {ev['club_name']}")

            # +20 same category
            if ev['category'] and ev['category'] in attended_categories:
                score += 20
                if not reasons:
                    reasons.append(f"Matches your interest in {ev['category']}")

            # +15 popularity (normalised — max 15 pts)
            pop = min(ev['attendance_count'], 100)
            score += int(pop * 0.15)
            if pop >= 20 and not reasons:
                reasons.append("Popular event")
            elif pop >= 50 and not any('Popular' in r for r in reasons):
                reasons.append("Trending")

            # +10 upcoming date bonus (within next 7 days)
            from datetime import date, timedelta
            try:
                ev_date = ev['date'] if hasattr(ev['date'], 'toordinal') else date.fromisoformat(str(ev['date']))
                if ev_date <= date.today() + timedelta(days=7):
                    score += 10
                    if not reasons:
                        reasons.append("Upcoming soon")
            except Exception:
                pass

            if not reasons:
                reasons.append("Upcoming event")

            ev['score']  = score
            ev['reason'] = reasons[0]  # primary reason for the badge
            scored.append(ev)

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:limit]

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
