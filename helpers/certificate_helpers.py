# helpers/certificate_helpers.py
import os
import uuid
import time
from PIL import Image, ImageDraw, ImageFont


# ── Font loader ────────────────────────────────────────────────────────────────
_FONT_PATHS = [
    "C:/Windows/Fonts/georgiab.ttf",
    "C:/Windows/Fonts/georgia.ttf",
    "C:/Windows/Fonts/times.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _centered_x(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return (width - (bbox[2] - bbox[0])) // 2


# ── Main generator ────────────────────────────────────────────────────────────
def generate_certificate(student_name: str, event_title: str, save_path: str,
                         club_name: str = None, event_date: str = None,
                         organizer_name: str = None,
                         cert_id: str = None) -> str:
    """
    Generate a premium dark-theme certificate PNG (1400×900, landscape).
    Returns save_path on success.
    """
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

    W, H = 1400, 900
    cert_id   = cert_id or str(uuid.uuid4())[:8].upper()
    issue_date = event_date or time.strftime('%B %d, %Y')

    # ── Canvas ────────────────────────────────────────────────────────────────
    img  = Image.new('RGB', (W, H), color=(11, 15, 20))
    draw = ImageDraw.Draw(img)

    # ── Dark gradient overlay (simulate) ──────────────────────────────────────
    for y in range(H):
        ratio = y / H
        r = int(11  + (22 - 11)  * ratio)
        g = int(15  + (30 - 15)  * ratio)
        b = int(20  + (42 - 20)  * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # ── Accent borders ────────────────────────────────────────────────────────
    # Outer border — emerald
    draw.rectangle([0, 0, W-1, H-1],  outline=(16, 185, 129), width=4)
    # Inner border — dimmer
    draw.rectangle([14, 14, W-15, H-15], outline=(22, 60, 44), width=1)

    # Top accent bar
    draw.rectangle([0, 0, W, 8], fill=(16, 185, 129))
    draw.rectangle([0, H-8, W, H], fill=(16, 185, 129))

    # Left/right accent columns
    draw.rectangle([0, 0, 8, H], fill=(16, 185, 129))
    draw.rectangle([W-8, 0, W, H], fill=(16, 185, 129))

    # ── Corner ornaments ──────────────────────────────────────────────────────
    corner_size = 40
    emerald = (16, 185, 129)
    for cx, cy in [(28, 28), (W-28, 28), (28, H-28), (W-28, H-28)]:
        draw.rectangle([cx-2, cy-2, cx+2, cy+2], fill=emerald)
        draw.ellipse([cx-14, cy-14, cx+14, cy+14], outline=emerald, width=1)

    # ── Watermark diagonal text ───────────────────────────────────────────────
    wm_font = _load_font(60)
    wm_img  = Image.new('RGBA', (600, 600), (0, 0, 0, 0))
    wm_draw = ImageDraw.Draw(wm_img)
    wm_draw.text((50, 250), "CECRMS", font=wm_font, fill=(16, 185, 129, 18))
    wm_rotated = wm_img.rotate(30, expand=False)
    img.paste(wm_rotated, (W//2 - 300, H//2 - 300), wm_rotated)

    # ── Fonts ─────────────────────────────────────────────────────────────────
    f_logo    = _load_font(20)
    f_cert    = _load_font(52)
    f_certify = _load_font(22)
    f_name    = _load_font(58)
    f_body    = _load_font(22)
    f_event   = _load_font(36)
    f_sub     = _load_font(18)
    f_id      = _load_font(15)

    # ── Header: CECRMS logo text ───────────────────────────────────────────────
    logo_text = "CECRMS"
    sub_text  = "Campus Event & Club Resource Management System"
    lx = _centered_x(draw, logo_text, f_cert, W)
    draw.text((lx, 38), logo_text, font=f_cert, fill=(16, 185, 129))
    sx = _centered_x(draw, sub_text, f_sub, W)
    draw.text((sx, 105), sub_text, font=f_sub, fill=(100, 150, 130))

    # Separator line
    draw.line([(100, 140), (W-100, 140)], fill=(22, 60, 44), width=1)

    # ── Title: Certificate of Participation ───────────────────────────────────
    title_text = "CERTIFICATE OF PARTICIPATION"
    tx = _centered_x(draw, title_text, f_certify, W)
    draw.text((tx, 165), title_text, font=f_certify, fill=(180, 220, 200))

    # ── Body ──────────────────────────────────────────────────────────────────
    cy_text = "This certifies that"
    draw.text((_centered_x(draw, cy_text, f_body, W), 230), cy_text,
              font=f_body, fill=(130, 160, 150))

    # Student name — highlight box
    name_bbox = draw.textbbox((0, 0), student_name, font=f_name)
    nw = name_bbox[2] - name_bbox[0]
    name_x = (W - nw) // 2
    # Background highlight
    pad = 14
    draw.rectangle([name_x - pad, 268, name_x + nw + pad, 340],
                   fill=(16, 185, 129, 0), outline=(16, 185, 129, 0))
    draw.text((name_x, 270), student_name, font=f_name, fill=(230, 255, 245))

    # Underline name
    draw.line([(name_x, 342), (name_x + nw, 342)],
              fill=(16, 185, 129), width=2)

    participated_text = "has successfully participated in"
    draw.text((_centered_x(draw, participated_text, f_body, W), 362),
              participated_text, font=f_body, fill=(130, 160, 150))

    # Event title
    # Wrap if too long
    max_event_chars = 55
    if len(event_title) > max_event_chars:
        event_title = event_title[:max_event_chars].rstrip() + "…"
    draw.text((_centered_x(draw, event_title, f_event, W), 398),
              event_title, font=f_event, fill=(16, 185, 129))

    # Club / organizer
    y_info = 460
    if club_name:
        club_label = f"Organised by  {club_name}"
        draw.text((_centered_x(draw, club_label, f_body, W), y_info),
                  club_label, font=f_body, fill=(100, 150, 130))
        y_info += 32

    # ── Separator ─────────────────────────────────────────────────────────────
    draw.line([(100, y_info + 10), (W-100, y_info + 10)],
              fill=(22, 60, 44), width=1)

    # ── Footer: signatures & certificate ID ───────────────────────────────────
    sig_y = y_info + 40

    # Left signature
    draw.line([(120, sig_y + 60), (400, sig_y + 60)],
              fill=(50, 80, 70), width=1)
    left_label = organizer_name if organizer_name else "Event Coordinator"
    draw.text((_centered_x(draw, left_label, f_sub, 520) + 60, sig_y + 68),
              left_label, font=f_sub, fill=(100, 130, 120))

    # Right signature
    draw.line([(W-400, sig_y + 60), (W-120, sig_y + 60)],
              fill=(50, 80, 70), width=1)
    draw.text((_centered_x(draw, "CECRMS Director", f_sub, 520) + W - 460, sig_y + 68),
              "CECRMS Director", font=f_sub, fill=(100, 130, 120))

    # Centre: Date
    draw.text((_centered_x(draw, f"Date: {issue_date}", f_sub, W), sig_y + 50),
              f"Date: {issue_date}", font=f_sub, fill=(100, 150, 130))

    # Certificate ID badge
    id_text = f"Certificate ID: {cert_id}"
    id_x    = _centered_x(draw, id_text, f_id, W)
    draw.rectangle([id_x - 10, H - 54, id_x + draw.textlength(id_text, f_id) + 10, H - 34],
                   fill=(16, 40, 32), outline=(16, 185, 129))
    draw.text((id_x, H - 54), id_text, font=f_id, fill=(100, 185, 150))

    img.save(save_path, "PNG", optimize=True)
    return save_path
