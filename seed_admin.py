"""seed_admin.py — Creates admin and sample club_admin users."""
from werkzeug.security import generate_password_hash
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', '127.0.0.1'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'cecrms'),
)
cur = conn.cursor()

users = [
    ('Admin',         'admin@cecrms.com',      'admin123', 'admin',      None),
    ('Club Coordinator', 'coord@cecrms.com',   'coord123', 'club_admin', None),
    ('Demo Student',  'student@cecrms.com',    'student123','student',   None),
]

for name, email, password, role, club_id in users:
    h = generate_password_hash(password)
    cur.execute("""
        INSERT INTO users (name, email, password_hash, role, club_id)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE role = VALUES(role), password_hash = VALUES(password_hash)
    """, (name, email, h, role, club_id))
    print(f"  Seeded: {email} ({role}) / password: {password}")

conn.commit()
cur.close()
conn.close()
print("Done.")
