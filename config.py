# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY       = os.getenv('SECRET_KEY', 'devsecret_change_in_prod')
    DB_HOST          = os.getenv('DB_HOST', '127.0.0.1')
    DB_USER          = os.getenv('DB_USER', 'root')
    DB_PASSWORD      = os.getenv('DB_PASSWORD', '')
    DB_NAME          = os.getenv('DB_NAME', 'cecrms')
    DB_POOL_SIZE     = int(os.getenv('DB_POOL_SIZE', '5'))
    DB_POOL_NAME     = os.getenv('DB_POOL_NAME', 'cecrms_pool')
    UPLOAD_FOLDER    = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    MAX_UPLOAD_BYTES = int(os.getenv('MAX_UPLOAD_BYTES', str(5 * 1024 * 1024)))  # 5 MB
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    QR_FOLDER        = os.getenv('QR_FOLDER', 'static/qrcodes')
    CERT_FOLDER      = os.getenv('CERT_FOLDER', 'static/certificates')
    QR_HMAC_KEY      = os.getenv('QR_HMAC_KEY', 'qr_secret')
    DEBUG            = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
