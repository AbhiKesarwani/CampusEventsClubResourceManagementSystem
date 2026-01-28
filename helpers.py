# helpers.py
import hmac, hashlib, time, os
from itsdangerous import URLSafeSerializer
import qrcode
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
load_dotenv()

QR_HMAC_KEY = os.getenv('QR_HMAC_KEY', 'qr_secret')

def sign_payload(payload_str: str) -> str:
    # returns hex signature
    return hmac.new(QR_HMAC_KEY.encode(), payload_str.encode(), hashlib.sha256).hexdigest()

def make_qr_payload(event_id: int, user_id: int, ts: int = None) -> str:
    if ts is None:
        ts = int(time.time())
    payload = f"{event_id}:{user_id}:{ts}"
    sig = sign_payload(payload)
    return f"{payload}:{sig}"

def verify_qr_payload(payload_with_sig: str, max_age_sec: int = 60*60*6) -> dict:
    # returns dict with event_id, user_id if valid else raise ValueError
    parts = payload_with_sig.split(":")
    if len(parts) != 4:
        raise ValueError("Invalid payload format")
    event_id, user_id, ts_str, sig = parts
    payload = ":".join(parts[:3])
    expected = sign_payload(payload)
    if not hmac.compare_digest(expected, sig):
        raise ValueError("Invalid signature")
    ts = int(ts_str)
    if abs(int(time.time()) - ts) > max_age_sec:
        raise ValueError("Payload expired")
    return {'event_id': int(event_id), 'user_id': int(user_id), 'ts': ts}

def generate_qr_image(payload: str, save_path: str):
    img = qrcode.make(payload)
    img.save(save_path)
    return save_path

def generate_certificate(student_name: str, event_title: str, save_path: str):
    # very simple certificate creation with PIL
    W, H = (1200, 800)
    image = Image.new('RGB', (W, H), color='white')
    draw = ImageDraw.Draw(image)
    # load a font (default if none)
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        title_f = ImageFont.truetype(font_path, 48)
        body_f = ImageFont.truetype(font_path, 28)
    except Exception:
        title_f = ImageFont.load_default()
        body_f = ImageFont.load_default()

    draw.text((W/2 - 300, 120), "Certificate of Participation", font=title_f, align="center")
    draw.text((180, 260), f"This certifies that", font=body_f)
    draw.text((180, 320), f"{student_name}", font=title_f)
    draw.text((180, 420), f"has participated in", font=body_f)
    draw.text((180, 470), f"{event_title}", font=title_f)
    draw.text((180, 600), f"Issue Date: {time.strftime('%Y-%m-%d')}", font=body_f)
    image.save(save_path)
    return save_path
