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
    Utilizes the full canvas area with balanced vertical rhythm.
    Signatures removed per Phase 3D specifications.
    Returns save_path on success.
    """
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

    W, H = 1400, 900
    cert_id   = cert_id or str(uuid.uuid4())[:8].upper()
    issue_date = event_date or time.strftime('%B %d, %Y')

    # ── Canvas ────────────────────────────────────────────────────────────────
    img  = Image.new('RGB', (W, H), color=(11, 15, 20))
    draw = ImageDraw.Draw(img)

    # ── Dark gradient background ──────────────────────────────────────────────
    for y in range(H):
        ratio = y / H
        r = int(11  + (22 - 11)  * ratio)
        g = int(15  + (30 - 15)  * ratio)
        b = int(20  + (42 - 20)  * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # ── Accent borders (Continuous Green & Purple Frames on all 4 sides) ───────
    emerald = (16, 185, 129)
    purple  = (124, 58, 237)
    # 1. Outer solid border — 8px continuous emerald frame on all 4 edges
    draw.rectangle([0, 0, W-1, H-1], outline=emerald, width=8)
    # 2. Continuous purple accent border on all 4 sides — cleanly connecting corners
    draw.rectangle([14, 14, W-15, H-15], outline=purple, width=2)
    # 3. Inner green border — clean inset line continuous on all 4 sides
    draw.rectangle([22, 22, W-23, H-23], outline=emerald, width=2)
    # 4. Secondary subtle decorative line
    draw.rectangle([28, 28, W-29, H-29], outline=(22, 60, 44), width=1)

    # ── Corner ornaments ──────────────────────────────────────────────────────
    for cx, cy in [(40, 40), (W-40, 40), (40, H-40), (W-40, H-40)]:
        draw.rectangle([cx-3, cy-3, cx+3, cy+3], fill=emerald)
        draw.ellipse([cx-14, cy-14, cx+14, cy+14], outline=emerald, width=1)

    # ── Watermark diagonal text ───────────────────────────────────────────────
    wm_font = _load_font(72)
    wm_img  = Image.new('RGBA', (700, 700), (0, 0, 0, 0))
    wm_draw = ImageDraw.Draw(wm_img)
    wm_draw.text((80, 300), "CampusOps", font=wm_font, fill=(16, 185, 129, 20))
    wm_rotated = wm_img.rotate(30, expand=False)
    img.paste(wm_rotated, (W//2 - 350, H//2 - 350), wm_rotated)

    # ── Fonts ─────────────────────────────────────────────────────────────────
    f_brand   = _load_font(54)
    f_sub     = _load_font(20)
    f_title   = _load_font(28)
    f_lead    = _load_font(24)
    f_name    = _load_font(64)
    f_event   = _load_font(42)
    f_info    = _load_font(22)
    f_id      = _load_font(18)

    # ── Header: CampusOps Branding ─────────────────────────────────────────────
    brand_text = "CampusOps"
    sub_text   = "Club Management System"
    bx = _centered_x(draw, brand_text, f_brand, W)
    draw.text((bx, 50), brand_text, font=f_brand, fill=(16, 185, 129))
    sx = _centered_x(draw, sub_text, f_sub, W)
    draw.text((sx, 120), sub_text, font=f_sub, fill=(110, 165, 145))

    # Top separator line
    draw.line([(140, 160), (W-140, 160)], fill=(28, 75, 55), width=2)

    # ── Title: Certificate of Participation ───────────────────────────────────
    title_text = "CERTIFICATE OF PARTICIPATION"
    tx = _centered_x(draw, title_text, f_title, W)
    draw.text((tx, 185), title_text, font=f_title, fill=(190, 235, 215))

    # ── Recipient Intro ───────────────────────────────────────────────────────
    cy_text = "This is proudly presented to"
    draw.text((_centered_x(draw, cy_text, f_lead, W), 255), cy_text,
              font=f_lead, fill=(140, 175, 165))

    # ── Student Name ──────────────────────────────────────────────────────────
    name_bbox = draw.textbbox((0, 0), student_name, font=f_name)
    nw = name_bbox[2] - name_bbox[0]
    name_x = (W - nw) // 2
    name_y = 300
    draw.text((name_x, name_y), student_name, font=f_name, fill=(240, 255, 250))

    # Underline below name
    draw.line([(name_x - 20, name_y + 80), (name_x + nw + 20, name_y + 80)],
              fill=(16, 185, 129), width=2)

    # ── Participation Body ────────────────────────────────────────────────────
    participated_text = "for successfully participating in"
    draw.text((_centered_x(draw, participated_text, f_lead, W), 415),
              participated_text, font=f_lead, fill=(140, 175, 165))

    # ── Event Title ───────────────────────────────────────────────────────────
    max_event_chars = 52
    display_event_title = event_title
    if len(display_event_title) > max_event_chars:
        display_event_title = display_event_title[:max_event_chars].rstrip() + "…"
    draw.text((_centered_x(draw, display_event_title, f_event, W), 465),
              display_event_title, font=f_event, fill=(16, 185, 129))

    # ── Club & Organizer Info ─────────────────────────────────────────────────
    if club_name:
        club_label = f"Organized by {club_name}"
        draw.text((_centered_x(draw, club_label, f_info, W), 540),
                  club_label, font=f_info, fill=(120, 170, 150))

    # ── Date ──────────────────────────────────────────────────────────────────
    date_label = f"Issued on {issue_date}"
    draw.text((_centered_x(draw, date_label, f_info, W), 605),
              date_label, font=f_info, fill=(140, 175, 165))

    # ── Bottom Separator ──────────────────────────────────────────────────────
    draw.line([(140, 675), (W-140, 675)], fill=(28, 75, 55), width=2)

    # ── Footer: Certificate ID & Verification Info ────────────────────────────
    id_text = f"Certificate ID: #{cert_id}"
    id_x    = _centered_x(draw, id_text, f_id, W)
    id_box_y = 725
    id_w    = draw.textlength(id_text, f_id)
    draw.rectangle([id_x - 16, id_box_y - 8, id_x + id_w + 16, id_box_y + 30],
                   fill=(14, 38, 30), outline=(16, 185, 129), width=1)
    draw.text((id_x, id_box_y), id_text, font=f_id, fill=(120, 210, 175))

    verify_sub = "Verified Academic Credential · CampusOps Verification System"
    vx = _centered_x(draw, verify_sub, _load_font(14), W)
    draw.text((vx, 780), verify_sub, font=_load_font(14), fill=(80, 125, 110))

    img.save(save_path, "PNG", optimize=True)
    return save_path

