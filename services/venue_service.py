# services/venue_service.py
from database import get_db_connection


def get_all_venues() -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM venues ORDER BY venue_name ASC")
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_venue_by_id(venue_id: int) -> dict | None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM venues WHERE venue_id = %s", (venue_id,))
        return cur.fetchone()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def create_venue(venue_name: str, capacity: int = None,
                 location: str = None, type_: str = None) -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO venues (venue_name, capacity, location, type) VALUES (%s,%s,%s,%s)",
            (venue_name, capacity, location, type_)
        )
        conn.commit()
        return cur.lastrowid
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def update_venue(venue_id: int, venue_name: str, capacity: int = None,
                 location: str = None, type_: str = None) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE venues SET venue_name=%s, capacity=%s, location=%s, type=%s WHERE venue_id=%s",
            (venue_name, capacity, location, type_, venue_id)
        )
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def delete_venue(venue_id: int) -> None:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM venues WHERE venue_id = %s", (venue_id,))
        conn.commit()
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_venues_for_select() -> list[dict]:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT venue_id, venue_name FROM venues ORDER BY venue_name")
        return cur.fetchall()
    finally:
        if cur: cur.close()
        if conn: conn.close()


def count_venues() -> int:
    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM venues")
        return cur.fetchone()[0]
    finally:
        if cur: cur.close()
        if conn: conn.close()
