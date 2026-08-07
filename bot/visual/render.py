from __future__ import annotations

import io
import pathlib
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .assets import card_image_path

FONTS_DIR = pathlib.Path("C:/Windows/Fonts")
PROJECT_FONTS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"
LINUX_FONTS_DIR = pathlib.Path("/usr/share/fonts/truetype/dejavu")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a TrueType font with project-local and OS fallbacks."""
    candidates: list[pathlib.Path] = []
    for base in (PROJECT_FONTS_DIR, FONTS_DIR, LINUX_FONTS_DIR):
        if not base.exists():
            continue
        candidates.extend([
            base / ("georgiab.ttf" if bold else "georgia.ttf"),
            base / "georgia.ttf",
            base / "arial.ttf",
            base / "segoeui.ttf",
            base / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
        ])
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def _background(w: int, h: int, seed: int | None = None) -> Image.Image:
    rng = random.Random(seed)
    base = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(base)
    top = (30, 18, 58)
    bottom = (6, 4, 14)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for _ in range(170):
        x = rng.uniform(0, w)
        y = rng.uniform(0, h)
        rad = rng.uniform(0.4, 1.7)
        alpha = rng.randint(60, 210)
        color = (255, 255, 255, alpha) if rng.random() < 0.8 else (255, 236, 190, alpha)
        odraw.ellipse([x - rad, y - rad, x + rad, y + rad], fill=color)
    overlay = overlay.filter(ImageFilter.GaussianBlur(0.4))
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


def _center_x(draw: ImageDraw.ImageDraw, w: int, text: str, font) -> int:
    x0, _, x1, _ = draw.textbbox((0, 0), text, font=font)
    return (w - (x1 - x0)) // 2


def _load_card(card) -> Image.Image | None:
    path = card_image_path(card)
    if path is None:
        return None
    img = Image.open(path).convert("RGB")
    return img


def _fit(img: Image.Image, w: int, h: int) -> Image.Image:
    return img.resize((w, h), Image.LANCZOS)


def _add_glow(img: Image.Image, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    pad = 36
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([x0 - pad, y0 - pad, x1 + pad, y1 + pad], fill=(140, 100, 210, 30))
    glow = glow.filter(ImageFilter.GaussianBlur(28))
    img.paste(Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB"))


def make_spread_image(spread_title: str, cards_info: list[dict], footer: str = "MOIRA") -> bytes:
    """cards_info: [{"label": str, "card": TarotCard, "reversed": bool, "name": str}]"""
    W, H = 1080, 1500
    img = _background(W, H, seed=len(spread_title))
    draw = ImageDraw.Draw(img)

    title_font = _font(46, bold=True)
    draw.text((_center_x(draw, W, spread_title, title_font), 64), spread_title, font=title_font, fill=(240, 235, 255))

    card_w, card_h = 300, 520
    gap = 42
    total = card_w * 3 + gap * 2
    x_start = (W - total) // 2
    y0 = 260

    pos_font = _font(26)
    name_font = _font(27, bold=True)
    note_font = _font(21)

    for i, info in enumerate(cards_info[:3]):
        x = x_start + i * (card_w + gap)
        label = info["label"]
        draw.text((_center_x_in(draw, x, card_w, label, pos_font), y0 - 44), label, font=pos_font, fill=(205, 195, 235))
        card_img = _load_card(info["card"])
        if card_img is not None:
            if info.get("reversed"):
                card_img = card_img.rotate(180)
            card_img = _fit(card_img, card_w, card_h)
            _add_glow(img, (x, y0, x + card_w, y0 + card_h))
            img.paste(card_img, (x, y0))
            draw = ImageDraw.Draw(img)
        name = info["name"]
        draw.text((_center_x_in(draw, x, card_w, name, name_font), y0 + card_h + 18), name, font=name_font, fill=(250, 246, 255))
        if info.get("reversed"):
            note = "перевёрнутая"
            draw.text((_center_x_in(draw, x, card_w, note, note_font), y0 + card_h + 54), note, font=note_font, fill=(190, 170, 215))

    foot_font = _font(22)
    draw.text((_center_x(draw, W, footer, foot_font), H - 64), footer, font=foot_font, fill=(150, 140, 180))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def make_share_image(
    spread_title: str, cards_info: list[dict], summary: str, footer: str = "MOIRA"
) -> bytes:
    """Square share card: title, drawn cards, short synthesis, footer brand."""
    W, H = 1080, 1080
    img = _background(W, H, seed=len(spread_title) * 3 + 1)
    draw = ImageDraw.Draw(img)

    title_font = _font(44, bold=True)
    title_lines = _wrap(draw, spread_title, title_font, W - 80)[:2]
    y = 56
    for line in title_lines:
        draw.text((_center_x(draw, W, line, title_font), y), line, font=title_font, fill=(240, 235, 255))
        y += 54

    card_w, card_h = 240, 416
    gap = 36
    total = card_w * len(cards_info[:3]) + gap * (len(cards_info[:3]) - 1)
    x_start = (W - total) // 2
    y0 = 200
    pos_font = _font(22)
    name_font = _font(22, bold=True)

    for i, info in enumerate(cards_info[:3]):
        x = x_start + i * (card_w + gap)
        label = info["label"]
        draw.text((_center_x_in(draw, x, card_w, label, pos_font), y0 - 34), label, font=pos_font, fill=(205, 195, 235))
        card_img = _load_card(info["card"])
        if card_img is not None:
            if info.get("reversed"):
                card_img = card_img.rotate(180)
            card_img = _fit(card_img, card_w, card_h)
            _add_glow(img, (x, y0, x + card_w, y0 + card_h))
            img.paste(card_img, (x, y0))
            draw = ImageDraw.Draw(img)
        name = info["name"] + (" ⟲" if info.get("reversed") else "")
        draw.text((_center_x_in(draw, x, card_w, name, name_font), y0 + card_h + 12), name, font=name_font, fill=(250, 246, 255))

    if summary:
        sum_font = _font(28)
        sum_lines = _wrap(draw, summary, sum_font, W - 120)[:4]
        y = 740
        for line in sum_lines:
            draw.text((_center_x(draw, W, line, sum_font), y), line, font=sum_font, fill=(225, 218, 245))
            y += 42

    foot_font = _font(24)
    draw.text((_center_x(draw, W, footer + " ✦ TAROT", foot_font), H - 64), footer + " ✦ TAROT", font=foot_font, fill=(150, 140, 180))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def make_single_image(header: str, subtitle: str, card, footer: str = "MOIRA", reversed_: bool = False) -> bytes:
    W, H = 1080, 1350
    img = _background(W, H, seed=len(header) * 7 + 3)
    draw = ImageDraw.Draw(img)

    head_font = _font(48, bold=True)
    header_lines = _wrap(draw, header, head_font, W - 80)
    y = 70
    for line in header_lines[:2]:
        draw.text((_center_x(draw, W, line, head_font), y), line, font=head_font, fill=(240, 235, 255))
        y += 58

    card_w, card_h = 430, 745
    x = (W - card_w) // 2
    y0 = 220
    card_img = _load_card(card)
    if card_img is not None:
        if reversed_:
            card_img = card_img.rotate(180)
        card_img = _fit(card_img, card_w, card_h)
        _add_glow(img, (x, y0, x + card_w, y0 + card_h))
        img.paste(card_img, (x, y0))
        draw = ImageDraw.Draw(img)

    sub_font = _font(34, bold=True)
    sub_lines = _wrap(draw, subtitle, sub_font, W - 100)
    y = y0 + card_h + 36
    for line in sub_lines[:2]:
        draw.text((_center_x(draw, W, line, sub_font), y), line, font=sub_font, fill=(250, 246, 255))
        y += 46

    foot_font = _font(22)
    draw.text((_center_x(draw, W, footer, foot_font), H - 60), footer, font=foot_font, fill=(150, 140, 180))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def _center_x_in(draw: ImageDraw.ImageDraw, slot_x: int, slot_w: int, text: str, font) -> int:
    x0, _, x1, _ = draw.textbbox((0, 0), text, font=font)
    w = x1 - x0
    if w > slot_w + 40:
        return slot_x - 20
    return slot_x + (slot_w - w) // 2


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        probe = (cur + " " + w).strip()
        x0, _, x1, _ = draw.textbbox((0, 0), probe, font=font)
        if x1 - x0 <= max_w:
            cur = probe
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
