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


# ── Gallery download helpers ────────────────────────────────────────────────
# Shared by routes/events.py and routes/clubs.py, which both offer a
# "download single image" / "download all as ZIP" gallery feature.

def get_image_path(images: list, img_id: int) -> str:
    """
    Find an image dict (each having 'img_id' and 'img_path' keys) by id and
    return its absolute filesystem path.
    Aborts with 404/403 if not found, invalid traversal, or missing on disk.
    """
    from flask import abort
    img = next((i for i in images if i['img_id'] == img_id), None)
    if not img or not img.get('img_path'):
        abort(404)
    if '..' in img['img_path'] or img['img_path'].startswith('/') or img['img_path'].startswith('\\'):
        abort(403)
    base_dir = os.path.abspath(os.path.join(os.getcwd(), 'static'))
    path = os.path.abspath(os.path.join(base_dir, img['img_path']))
    if not path.startswith(base_dir) or not os.path.exists(path):
        abort(404)
    return path


def build_gallery_zip(images: list):
    """Build an in-memory ZIP archive containing every given image safely. Returns a BytesIO."""
    import io
    import zipfile
    base_dir = os.path.abspath(os.path.join(os.getcwd(), 'static'))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for img in images:
            img_path = img.get('img_path') if isinstance(img, dict) else getattr(img, 'img_path', None)
            if not img_path or '..' in img_path:
                continue
            path = os.path.abspath(os.path.join(base_dir, img_path))
            if path.startswith(base_dir) and os.path.exists(path):
                zf.write(path, os.path.basename(path))
    buf.seek(0)
    return buf
