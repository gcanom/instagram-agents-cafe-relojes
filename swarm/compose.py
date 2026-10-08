"""Maquetación: superpone el texto de cada slide sobre la imagen generada (FLUX no debe escribir texto)."""
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
]
CREAM = (245, 237, 224)


def _font(size: int):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur] if cur else lines


def overlay(data: bytes, text: str, index: int | None = None, total: int | None = None) -> bytes:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size
    margin = int(w * 0.08)
    font = _font(int(w * 0.058))
    draw = ImageDraw.Draw(img)
    lines = _wrap(draw, text, font, w - 2 * margin)
    line_h = int(font.size * 1.25)
    block_h = line_h * len(lines)

    # degradado inferior para legibilidad
    band_top = max(0, h - block_h - margin * 2 - int(h * 0.22))
    grad = Image.new("L", (1, h - band_top))
    for y in range(h - band_top):
        grad.putpixel((0, y), int(238 * min(1.0, (y / (h - band_top)) * 1.5) ** 1.1))
    shade = Image.new("RGB", (w, h - band_top), (24, 14, 8))
    img.paste(shade, (0, band_top), grad.resize((w, h - band_top)))

    draw = ImageDraw.Draw(img)
    y = h - margin - block_h - int(h * 0.02)
    for line in lines:
        draw.text((margin, y), line, font=font, fill=CREAM)
        y += line_h
    if index and total:
        small = _font(int(w * 0.03))
        draw.text((margin, h - int(margin * 0.8)), f"{index}/{total}", font=small, fill=(200, 188, 170))

    out = io.BytesIO()
    img.save(out, "JPEG", quality=92)
    return out.getvalue()
