# helpers/certificate_helpers.py
import os
import time
from PIL import Image, ImageDraw, ImageFont


def generate_certificate(student_name: str, event_title: str, save_path: str) -> str:
    """
    Generate a certificate PNG using PIL.
    Returns save_path on success.
    """
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    W, H = 1200, 800
    bg_color = (245, 248, 255)
    image = Image.new('RGB', (W, H), color=bg_color)
    draw  = ImageDraw.Draw(image)

    # --- border ---
    draw.rectangle([20, 20, W - 20, H - 20], outline=(100, 130, 220), width=5)
    draw.rectangle([30, 30, W - 30, H - 30], outline=(180, 200, 240), width=2)

    # --- fonts ---
    font_paths = [
        "C:/Windows/Fonts/georgiab.ttf",
        "C:/Windows/Fonts/times.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]

    def load_font(size):
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()

    title_f    = load_font(52)
    heading_f  = load_font(38)
    body_f     = load_font(28)
    sub_f      = load_font(22)

    # --- header ---
    draw.text((W // 2, 80),  "CECRMS",
              font=load_font(36), fill=(80, 100, 200), anchor="mm")
    draw.text((W // 2, 130), "Campus Event & Club Resource Management System",
              font=sub_f, fill=(120, 130, 160), anchor="mm")

    # --- title ---
    draw.text((W // 2, 230), "Certificate of Participation",
              font=title_f, fill=(40, 60, 160), anchor="mm")

    # --- body ---
    draw.text((W // 2, 330), "This certifies that",
              font=body_f, fill=(80, 80, 100), anchor="mm")
    draw.text((W // 2, 400), student_name,
              font=heading_f, fill=(20, 40, 120), anchor="mm")
    draw.text((W // 2, 460), "has successfully participated in",
              font=body_f, fill=(80, 80, 100), anchor="mm")
    draw.text((W // 2, 520), event_title,
              font=heading_f, fill=(20, 40, 120), anchor="mm")

    # --- footer ---
    issue_date = time.strftime('%B %d, %Y')
    draw.text((W // 2, 650), f"Issue Date: {issue_date}",
              font=sub_f, fill=(100, 100, 130), anchor="mm")
    draw.line([(200, 720), (500, 720)], fill=(160, 160, 190), width=2)
    draw.line([(700, 720), (1000, 720)], fill=(160, 160, 190), width=2)
    draw.text((350, 740), "Authorized Signature",
              font=sub_f, fill=(120, 120, 150), anchor="mm")
    draw.text((850, 740), "Date",
              font=sub_f, fill=(120, 120, 150), anchor="mm")

    image.save(save_path, "PNG")
    return save_path
