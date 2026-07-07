# helpers/upload_helpers.py
import os
import time
from flask import current_app
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
MAX_UPLOAD_BYTES   = 5 * 1024 * 1024  # 5 MB


def _allowed(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_upload(file_storage) -> tuple[bool, str]:
    """
    Returns (ok, error_message).
    file_storage is a Werkzeug FileStorage object.
    """
    if not file_storage or not file_storage.filename:
        return False, "No file provided."
    if not _allowed(file_storage.filename):
        return False, f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    file_storage.seek(0, 2)          # seek to end
    size = file_storage.tell()
    file_storage.seek(0)             # reset
    if size > MAX_UPLOAD_BYTES:
        return False, f"File too large (max {MAX_UPLOAD_BYTES // (1024*1024)} MB)."
    return True, ""


def save_upload(file_storage, prefix: str) -> str:
    """
    Validates and saves a FileStorage to UPLOAD_FOLDER.
    Returns the relative path string (e.g. 'uploads/event_3_161234.jpg').
    Raises ValueError if validation fails.
    """
    ok, msg = validate_upload(file_storage)
    if not ok:
        raise ValueError(msg)

    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
    os.makedirs(upload_folder, exist_ok=True)

    ext      = file_storage.filename.rsplit('.', 1)[1].lower()
    filename = f"{prefix}_{int(time.time())}.{ext}"
    filename = secure_filename(filename)
    full_path = os.path.join(upload_folder, filename)
    file_storage.save(full_path)
    return f"uploads/{filename}"


def delete_upload(relative_path: str):
    """Delete a file given its relative path (e.g. 'uploads/foo.jpg')."""
    if not relative_path:
        return
    full_path = os.path.join('static', relative_path)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except OSError:
            pass
