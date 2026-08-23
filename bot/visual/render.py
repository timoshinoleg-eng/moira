"""Pillow renderers for Moira: spread, share and single-card images.

All visual constants (colors, fonts, sizes, spacing) come from ``tokens.py`` —
no magic numbers here. Font resolution order: project-local PT Serif → OS
fallbacks → PIL default font. Text is sanitized (HTML tags + glyphs missing
from the font) before drawing.
"""
from __future__ import annotations

import io
import pathlib
import random
import re

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from . import tokens as T
from .assets import card_image_path

FONTS_DIR = pathlib.Path("C:/Windows/Fonts")  # legacy Windows fallback
PROJECT_FONTS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"
LINUX_FONTS_DIR = pathlib.Path("/usr/share/fonts/truetype/dejavu")

_TAG_RE = re.compile(r"<[^>]+>")
# Glyphs absent from PT Serif (verified via fontTools cmap): emoji, arrows,
# geometric shapes, misc symbols and dingbats render as .notdef boxes.
_UNSUPPORTED_RE = re.compile(
    "[\U0001F000-\U0001FAFF\u2190-\u21FF\u25A0-\u25FF\u2600-\u27BF\u2B00-\u2BFF]"
)


def _sanitize_text(text: str | None) -> str:
    """Strip HTML tags and glyphs the current font cannot render."""
    if not text:
        return ""
    text = _TAG_RE.sub("", text)
    text = _UNSUPPORTED_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a TrueType font: project PT Serif first, then OS fallbacks, then PIL default."""
    primary = T.FONT_BOLD if bold else T.FONT_REGULAR
    fallback = T.FONT_FALLBACK_BOLD if bold else T.FONT_FALLBACK_REGULAR
    candidates: list[pathlib.Path] = []
    for base in (PROJECT_FONTS_DIR, FONTS_DIR, LINUX_FONTS_DIR):
        if not base.exists():
            continue
        candidates += [
            base / primary,
            base / fallback,
            base / ("georgiab.ttf" if bold else "georgia.ttf"),
            base / "arial.ttf",
            base / "segoeui.ttf",
        ]
    seen: set[pathlib.Path] = set()
    for p in candidates:
        if p.exists() and p not in seen:
            seen.add(p)
            return ImageFont.truetype(str(p), size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # pragma: no cover - very old Pillow
        return ImageFont.load_default()


def _background(w: int, h: int, seed: int | None = None) -> Image.Image:
    """Vertical night-sky gradient with a soft star field (tokens-driven)."""
    rng = random.Random(seed)
    base = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(base)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(T.BG_TOP[0] + (T.BG_BOTTOM[0] - T.BG_TOP[0]) * t)
        g = int(T.BG_TOP[1] + (T.BG_BOTTOM[1] - T.BG_TOP[1]) * t)
        b = int(T.BG_TOP[2] + (T.BG_BOTTOM[2] - T.BG_TOP[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for _ in range(T.BG_STARS):
        x = rng.uniform(0, w)
        y = rng.uniform(0, h)
        rad = rng.uniform(*T.STAR_RADIUS)
        alpha = rng.randint(*T.STAR_ALPHA)
        color = (255, 255, 255, alpha) if rng.random() >= T.STAR_GOLD_CHANCE else (255, 236, 190, alpha)
        odraw.ellipse([x - rad, y - rad, x + rad, y + rad], fill=color)
    overlay = overlay.filter(ImageFilter.GaussianBlur(T.STAR_BLUR))
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


VISUAL_PACK_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "generated_visuals" / "2026-08-17"


def _asset_background(name: str, w: int, h: int, seed: int | None = None) -> Image.Image:
    """Use a generated visual plate when present; preserve deterministic fallback."""
    path = VISUAL_PACK_DIR / name
    if path.exists():
        try:
            source = Image.open(path).convert("RGB")
            return ImageOps.fit(source, (w, h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.48))
        except (OSError, ValueError):
            pass
    return _background(w, h, seed=seed)


def _paste_overlay(img: Image.Image, name: str, max_w: int, max_h: int, center: tuple[int, int]) -> None:
    """Paste a transparent overlay if the optional visual pack is available."""
    path = VISUAL_PACK_DIR / name
    if not path.exists():
        return
    try:
        overlay = Image.open(path).convert("RGBA")
        scale = min(max_w / overlay.width, max_h / overlay.height, 1.0)
        size = (max(1, int(overlay.width * scale)), max(1, int(overlay.height * scale)))
        overlay = overlay.resize(size, Image.Resampling.LANCZOS)
        x = int(center[0] - size[0] / 2)
        y = int(center[1] - size[1] / 2)
        img.paste(overlay, (x, y), overlay)
    except (OSError, ValueError):
        return


def _shade_region(img: Image.Image, box: tuple[int, int, int, int]) -> None:
    """Add a translucent local shade to protect text over atmospheric plates."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle(box, fill=T.READABILITY_SHADE)
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


def _center_x(draw: ImageDraw.ImageDraw, w: int, text: str, font) -> int:

    x0, _, x1, _ = draw.textbbox((0, 0), text, font=font)
    return (w - (x1 - x0)) // 2


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


def _load_card(card) -> Image.Image | None:
    path = card_image_path(card)
    if path is None:
        return None
    return Image.open(path).convert("RGB")


def _fit(img: Image.Image, w: int, h: int) -> Image.Image:
    return img.resize((w, h), Image.LANCZOS)


def _add_glow(img: Image.Image, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    pad = T.GLOW_PAD
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([x0 - pad, y0 - pad, x1 + pad, y1 + pad], fill=T.GLOW_COLOR)
    glow = glow.filter(ImageFilter.GaussianBlur(T.GLOW_BLUR))
    img.paste(Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB"))


def _place_card(img: Image.Image, draw: ImageDraw.ImageDraw, card, x: int, y: int,
                w: int, h: int, reversed_: bool) -> ImageDraw.ImageDraw:
    """Paste the card (rotated when reversed) or draw a placeholder panel."""
    card_img = _load_card(card)
    if card_img is not None:
        if reversed_:
            card_img = card_img.rotate(180)
        _add_glow(img, (x, y, x + w, y + h))
        matte = T.CARD_MATTE_PADDING
        draw.rounded_rectangle(
            [x - matte, y - matte, x + w + matte, y + h + matte],
            radius=T.CARD_MATTE_RADIUS, fill=T.CARD_MATTE_FILL,
            outline=T.CARD_MATTE_OUTLINE, width=T.CARD_MATTE_WIDTH,
        )
        inset = T.CARD_INSET
        img.paste(_fit(card_img, w - inset * 2, h - inset * 2), (x + inset, y + inset))
        outline = T.CARD_FRAME_REVERSED_OUTLINE if reversed_ else T.CARD_FRAME_OUTLINE
        draw.rounded_rectangle(
            [x, y, x + w, y + h], radius=T.CARD_FRAME_RADIUS,
            outline=outline, width=T.CARD_FRAME_WIDTH,
        )
    else:
        draw.rounded_rectangle(
            [x, y, x + w, y + h], radius=T.PLACEHOLDER_RADIUS,
            fill=T.PLACEHOLDER_FILL, outline=T.PLACEHOLDER_OUTLINE,
            width=T.PLACEHOLDER_BORDER_WIDTH,
        )
    return ImageDraw.Draw(img)


def make_spread_image(
    spread_title: str, cards_info: list[dict], footer: str = "MOIRA", lang: str = "ru"
) -> bytes:
    """Three-card reading photo. cards_info: [{"label", "card", "reversed", "name"}]."""
    W, H = T.CANVAS_SPREAD
    img = _asset_background("moira_altar_portrait.jpg", W, H, seed=len(spread_title))
    _shade_region(img, T.SPREAD_TOP_SHADE)
    draw = ImageDraw.Draw(img)
    _paste_overlay(img, "moira_sigil_clean.png", 150, 150, (W // 2, H - 150))

    reversed_note = T.REVERSED_NOTE.get(lang, "reversed")

    title_font = _font(T.FONT_SPREAD_TITLE, bold=True)
    title = _sanitize_text(spread_title)
    draw.text((_center_x(draw, W, title, title_font), T.SPREAD_TITLE_Y), title, font=title_font, fill=T.TEXT_TITLE)

    card_w, card_h = T.SPREAD_CARD_SIZE
    gap = T.SPREAD_CARD_GAP
    total = card_w * 3 + gap * 2
    x_start = (W - total) // 2
    y0 = T.SPREAD_CARDS_Y

    pos_font = _font(T.FONT_SPREAD_POSITION)
    name_font = _font(T.FONT_SPREAD_NAME, bold=True)
    note_font = _font(T.FONT_SPREAD_NOTE)

    for i, info in enumerate(cards_info[:3]):
        x = x_start + i * (card_w + gap)
        label = _sanitize_text(info["label"])
        draw.text((_center_x_in(draw, x, card_w, label, pos_font), y0 + T.SPREAD_LABEL_OFFSET_Y),
                  label, font=pos_font, fill=T.TEXT_POSITION)
        draw = _place_card(img, draw, info["card"], x, y0, card_w, card_h, bool(info.get("reversed")))
        name = _sanitize_text(info["name"])
        draw.text((_center_x_in(draw, x, card_w, name, name_font), y0 + card_h + T.SPREAD_NAME_OFFSET_Y),
                  name, font=name_font, fill=T.TEXT_PRIMARY)
        if info.get("reversed"):
            draw.text((_center_x_in(draw, x, card_w, reversed_note, note_font), y0 + card_h + T.SPREAD_NOTE_OFFSET_Y),
                      reversed_note, font=note_font, fill=T.TEXT_REVERSED)

    foot_font = _font(T.FONT_SPREAD_FOOTER)
    foot = _sanitize_text(footer)
    draw.text((_center_x(draw, W, foot, foot_font), H + T.SPREAD_FOOTER_OFFSET_Y), foot, font=foot_font, fill=T.TEXT_FOOTER)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=T.JPEG_QUALITY)
    return buf.getvalue()


def make_share_image(
    spread_title: str, cards_info: list[dict], summary: str, footer: str = "MOIRA", lang: str = "ru"
) -> bytes:
    """Square share card: title, drawn cards, short synthesis, footer brand."""
    W, H = T.CANVAS_SHARE
    img = _asset_background("moira_share_background.jpg", W, H, seed=len(spread_title) * 3 + 1)
    _paste_overlay(img, "moira_thread_overlay_vector.png", 920, 420, (W // 2, 430))
    draw = ImageDraw.Draw(img)

    title_font = _font(T.FONT_SHARE_TITLE, bold=True)
    title_lines = _wrap(draw, _sanitize_text(spread_title), title_font, T.SHARE_TITLE_MAX_WIDTH)[:T.SHARE_TITLE_MAX_LINES]
    y = T.SHARE_TITLE_Y
    for line in title_lines:
        draw.text((_center_x(draw, W, line, title_font), y), line, font=title_font, fill=T.TEXT_TITLE)
        y += T.SHARE_TITLE_STEP

    card_w, card_h = T.SHARE_CARD_SIZE
    gap = T.SHARE_CARD_GAP
    n = len(cards_info[:3])
    total = card_w * n + gap * (n - 1)
    x_start = (W - total) // 2
    y0 = T.SHARE_CARDS_Y
    pos_font = _font(T.FONT_SHARE_POSITION)
    name_font = _font(T.FONT_SHARE_NAME, bold=True)
    marker = T.SHARE_REVERSED_MARKER.get(lang, " (reversed)")

    for i, info in enumerate(cards_info[:3]):
        x = x_start + i * (card_w + gap)
        label = _sanitize_text(info["label"])
        draw.text((_center_x_in(draw, x, card_w, label, pos_font), y0 + T.SHARE_LABEL_OFFSET_Y),
                  label, font=pos_font, fill=T.TEXT_POSITION)
        draw = _place_card(img, draw, info["card"], x, y0, card_w, card_h, bool(info.get("reversed")))
        name = _sanitize_text(info["name"]) + (marker if info.get("reversed") else "")
        draw.text((_center_x_in(draw, x, card_w, name, name_font), y0 + card_h + T.SHARE_NAME_OFFSET_Y),
                  name, font=name_font, fill=T.TEXT_PRIMARY)

    if summary:
        sum_font = _font(T.FONT_SHARE_SUMMARY)
        sum_lines = _wrap(draw, _sanitize_text(summary), sum_font, T.SHARE_SUMMARY_MAX_WIDTH)[:T.SHARE_SUMMARY_MAX_LINES]
        y = T.SHARE_SUMMARY_Y
        for line in sum_lines:
            draw.text((_center_x(draw, W, line, sum_font), y), line, font=sum_font, fill=T.TEXT_SECONDARY)
            y += T.SHARE_SUMMARY_STEP

    _paste_overlay(img, "moira_sigil_clean.png", 90, 90, (W // 2, 930))
    foot_font = _font(T.FONT_SHARE_FOOTER)
    foot = _sanitize_text(footer + " \u2726 TAROT")

    draw.text((_center_x(draw, W, foot, foot_font), H + T.SHARE_FOOTER_OFFSET_Y), foot, font=foot_font, fill=T.TEXT_FOOTER)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=T.JPEG_QUALITY)
    return buf.getvalue()


def make_single_image(
    header: str, subtitle: str, card, footer: str = "MOIRA", reversed_: bool = False, lang: str = "ru"
) -> bytes:
    """Single card banner: altar, card of the day or quiz result."""
    W, H = T.CANVAS_SINGLE
    img = _asset_background("moira_altar_portrait.jpg", W, H, seed=len(header) * 7 + 3)
    _shade_region(img, T.SINGLE_TOP_SHADE)
    draw = ImageDraw.Draw(img)

    head_font = _font(T.FONT_SINGLE_HEADER, bold=True)
    header_lines = _wrap(draw, _sanitize_text(header), head_font, T.SINGLE_HEADER_MAX_WIDTH)[:T.SINGLE_HEADER_MAX_LINES]
    y = T.SINGLE_HEADER_Y
    for line in header_lines:
        draw.text((_center_x(draw, W, line, head_font), y), line, font=head_font, fill=T.TEXT_TITLE)
        y += T.SINGLE_HEADER_STEP

    card_w, card_h = T.SINGLE_CARD_SIZE
    x = (W - card_w) // 2
    y0 = T.SINGLE_CARDS_Y
    draw = _place_card(img, draw, card, x, y0, card_w, card_h, reversed_)

    sub_font = _font(T.FONT_SINGLE_SUBTITLE, bold=True)
    sub_lines = _wrap(draw, _sanitize_text(subtitle), sub_font, T.SINGLE_SUBTITLE_MAX_WIDTH)[:T.SINGLE_SUBTITLE_MAX_LINES]
    y = y0 + card_h + T.SINGLE_SUBTITLE_OFFSET_Y
    for line in sub_lines:
        draw.text((_center_x(draw, W, line, sub_font), y), line, font=sub_font, fill=T.TEXT_PRIMARY)
        y += T.SINGLE_SUBTITLE_STEP

    foot_font = _font(T.FONT_SINGLE_FOOTER)
    foot = _sanitize_text(footer)
    draw.text((_center_x(draw, W, foot, foot_font), H + T.SINGLE_FOOTER_OFFSET_Y), foot, font=foot_font, fill=T.TEXT_FOOTER)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=T.JPEG_QUALITY)
    return buf.getvalue()
