# database.py
import os
import mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'database': os.getenv('DB_NAME', 'cecrms'),
    'autocommit': True
}

def get_db_connection():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn
