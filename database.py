# database.py
import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name=os.getenv('DB_POOL_NAME', 'cecrms_pool'),
            pool_size=int(os.getenv('DB_POOL_SIZE', '5')),
            pool_reset_session=True,
            host=os.getenv('DB_HOST', '127.0.0.1'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'cecrms'),
            autocommit=False,
        )
    return _pool

def get_db_connection():
    """Return a pooled MySQL connection."""
    try:
        return _get_pool().get_connection()
    except Exception:
        # Fallback: direct connection (dev / pool exhausted)
        return mysql.connector.connect(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'cecrms'),
            autocommit=False,
        )
