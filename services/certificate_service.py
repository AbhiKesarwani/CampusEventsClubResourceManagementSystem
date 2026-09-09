# services/certificate_service.py
import os
import uuid
from database import get_db_connection
from helpers.certificate_helpers import generate_certificate as _gen_cert


CERT_FOLDER = os.getenv('CERT_FOLDER', 'static/certificates')


def get_user_certificates(user_id: int) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT cert.*,
                   e.title  AS event_title,
                   e.date   AS event_date,
                   c.club_name,
                   u.name   AS coordinator_name
            FROM certificates cert
            JOIN events e ON cert.event_id = e.event_id
            LEFT JOIN clubs c ON e.club_id = c.club_id
            LEFT JOIN users u ON c.coordinator_id = u.user_id
            WHERE cert.user_id = %s
            ORDER BY cert.issue_date DESC
        """, (user_id,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_all_certificates(limit: int = 5000) -> list[dict]:
    """System-wide certificate list for admin exports."""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT cert.cert_id, u.name AS student_name, u.email AS student_email,
                   e.title AS event_title, c.club_name, cert.issue_date
            FROM certificates cert
            JOIN users  u ON cert.user_id  = u.user_id
            JOIN events e ON cert.event_id = e.event_id
            LEFT JOIN clubs c ON e.club_id = c.club_id
            ORDER BY cert.issue_date DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def search_certificates(query: str, user_id: int, role: str, limit: int = 10) -> list[dict]:
    """
    Search certificates by event title (and student name for admins), used by
    the global Ctrl+K search. Students only ever see their own certificates;
    admins can search across everyone's.
    """
    like = f"%{query}%"
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        if role == 'admin':
            cur.execute("""
                SELECT cert.cert_id, cert.event_id, cert.user_id, cert.issue_date,
                       e.title AS event_title, u.name AS student_name
                FROM certificates cert
                JOIN events e ON cert.event_id = e.event_id
                JOIN users  u ON cert.user_id  = u.user_id
                WHERE e.title LIKE %s OR u.name LIKE %s
                ORDER BY cert.issue_date DESC
                LIMIT %s
            """, (like, like, limit))
        else:
            cur.execute("""
                SELECT cert.cert_id, cert.event_id, cert.user_id, cert.issue_date,
                       e.title AS event_title, u.name AS student_name
                FROM certificates cert
                JOIN events e ON cert.event_id = e.event_id
                JOIN users  u ON cert.user_id  = u.user_id
                WHERE cert.user_id = %s AND e.title LIKE %s
                ORDER BY cert.issue_date DESC
                LIMIT %s
            """, (user_id, like, limit))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def certificate_exists(event_id: int, user_id: int) -> dict | None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM certificates WHERE event_id=%s AND user_id=%s",
            (event_id, user_id)
        )
        return cur.fetchone()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def _get_event_meta(event_id: int) -> dict:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT e.title, e.date,
                   c.club_name,
                   u.name AS coordinator_name
            FROM events e
            LEFT JOIN clubs c ON e.club_id = c.club_id
            LEFT JOIN users u ON c.coordinator_id = u.user_id
            WHERE e.event_id = %s
        """, (event_id,))
        return cur.fetchone() or {}
    finally:
        if cur: cur.close()
        if conn: conn.close()


def issue_certificate(event_id: int, user_id: int,
                      student_name: str, event_title: str) -> dict:
    """
    Generate certificate PNG and insert into DB.
    If one already exists, return existing record (no duplicate).
    """
    existing = certificate_exists(event_id, user_id)
    if existing:
        return existing

    os.makedirs(CERT_FOLDER, exist_ok=True)
    cert_id   = str(uuid.uuid4())[:8].upper()
    filename  = f"cert_{event_id}_{user_id}.png"
    save_path = os.path.join(CERT_FOLDER, filename)
    rel_path  = f"certificates/{filename}"

    # Fetch extra meta for rich certificate
    meta = _get_event_meta(event_id)
    event_date = None
    if meta.get('date'):
        try:
            event_date = meta['date'].strftime('%B %d, %Y')
        except Exception:
            event_date = str(meta['date'])

    _gen_cert(
        student_name=student_name,
        event_title=event_title,
        save_path=save_path,
        club_name=meta.get('club_name'),
        event_date=event_date,
        organizer_name=meta.get('coordinator_name'),
        cert_id=cert_id
    )

    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """INSERT INTO certificates (event_id, user_id, issue_date, cert_path)
               VALUES (%s,%s,CURDATE(),%s)""",
            (event_id, user_id, rel_path)
        )
        conn.commit()
        cur.execute("SELECT * FROM certificates WHERE event_id=%s AND user_id=%s",
                    (event_id, user_id))
        return cur.fetchone()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()
