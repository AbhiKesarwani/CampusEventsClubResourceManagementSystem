# helpers/qr_helpers.py
import hmac
import hashlib
import time
import os
import qrcode
from dotenv import load_dotenv

load_dotenv()

_QR_KEY = os.getenv('QR_HMAC_KEY', 'qr_secret')


def _sign(payload_str: str) -> str:
    return hmac.new(_QR_KEY.encode(), payload_str.encode(), hashlib.sha256).hexdigest()


def make_qr_payload(event_id: int, user_id: int, ts: int = None) -> str:
    """Create a signed QR payload string: event_id:user_id:ts:sig"""
    if ts is None:
        ts = int(time.time())
    payload = f"{event_id}:{user_id}:{ts}"
    sig = _sign(payload)
    return f"{payload}:{sig}"


def verify_qr_payload(payload_with_sig: str, max_age_sec: int = 6 * 3600) -> dict:
    """
    Verify and parse QR payload.
    Returns dict with event_id, user_id, ts or raises ValueError.
    """
    parts = payload_with_sig.strip().split(":")
    if len(parts) != 4:
        raise ValueError("Invalid QR payload format")
    event_id, user_id, ts_str, sig = parts
    payload = ":".join(parts[:3])
    expected = _sign(payload)
    if not hmac.compare_digest(expected, sig):
        raise ValueError("QR signature invalid")
    ts = int(ts_str)
    if abs(int(time.time()) - ts) > max_age_sec:
        raise ValueError("QR code has expired")
    return {'event_id': int(event_id), 'user_id': int(user_id), 'ts': ts}


def generate_qr_image(payload: str, save_path: str) -> str:
    """Generate and save a QR code PNG. Returns save_path."""
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    img = qrcode.make(payload)
    img.save(save_path)
    return save_path
