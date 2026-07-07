# services/certificate_service.py
import os
from database import get_db_connection
from helpers.certificate_helpers import generate_certificate as _gen_cert


CERT_FOLDER = os.getenv('CERT_FOLDER', 'static/certificates')


def get_user_certificates(user_id: int) -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT cert.*, e.title AS event_title, e.date AS event_date
            FROM certificates cert
            JOIN events e ON cert.event_id = e.event_id
            WHERE cert.user_id = %s
            ORDER BY cert.issue_date DESC
        """, (user_id,))
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


def issue_certificate(event_id: int, user_id: int, student_name: str, event_title: str) -> dict:
    """Generate PDF (PNG) cert and insert into DB. Returns cert record."""
    # Check if already exists
    existing = certificate_exists(event_id, user_id)
    if existing:
        return existing

    os.makedirs(CERT_FOLDER, exist_ok=True)
    filename  = f"cert_{event_id}_{user_id}.png"
    save_path = os.path.join(CERT_FOLDER, filename)
    rel_path  = f"certificates/{filename}"

    _gen_cert(student_name, event_title, save_path)

    conn = cur = None
    try:
        import time
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "INSERT INTO certificates (event_id, user_id, issue_date, cert_path) VALUES (%s,%s,CURDATE(),%s)",
            (event_id, user_id, rel_path)
        )
        conn.commit()
        cur.execute("SELECT * FROM certificates WHERE event_id=%s AND user_id=%s", (event_id, user_id))
        return cur.fetchone()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def count_user_certificates(user_id: int) -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM certificates WHERE user_id=%s", (user_id,))
        return cur.fetchone()[0]
    finally:
        if cur: cur.close()
        if conn: conn.close()
