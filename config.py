# config.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central application configuration, sourced entirely from environment
    variables (see .env). Never hardcode secrets here."""

    # ── Core Flask ──────────────────────────────────────────────────────────
    SECRET_KEY = os.getenv('SECRET_KEY', 'devsecret_change_in_prod')
    DEBUG      = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'

    # ── Session / cookie security ──────────────────────────────────────────
    # SESSION_COOKIE_SECURE should be 'true' in production (HTTPS only).
    # Left 'false' by default so local HTTP development still works.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE   = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

    # ── Database ────────────────────────────────────────────────────────────
    DB_HOST      = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT      = int(os.getenv('DB_PORT', '3306'))
    DB_USER      = os.getenv('DB_USER', 'root')
    DB_PASSWORD  = os.getenv('DB_PASSWORD', '')
    DB_NAME      = os.getenv('DB_NAME', 'cecrms')
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
    DB_POOL_NAME = os.getenv('DB_POOL_NAME', 'cecrms_pool')

    # ── File uploads ────────────────────────────────────────────────────────
    UPLOAD_FOLDER    = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    MAX_UPLOAD_BYTES = int(os.getenv('MAX_UPLOAD_BYTES', str(5 * 1024 * 1024)))  # 5 MB
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    CERT_FOLDER = os.getenv('CERT_FOLDER', 'static/certificates')

    # ── Campus Connect — AI (OpenRouter) ───────────────────────────────────
    # API key is read ONLY from the environment — never hardcode it.
    OPENROUTER_API_KEY         = os.getenv('OPENROUTER_API_KEY', '')
    OPENROUTER_MODEL           = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
    OPENROUTER_FALLBACK_MODELS = os.getenv('OPENROUTER_FALLBACK_MODELS', '')
    OPENROUTER_TIMEOUT         = int(os.getenv('OPENROUTER_TIMEOUT', '20'))
