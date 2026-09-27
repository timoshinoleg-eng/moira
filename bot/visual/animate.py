"""Card-by-card reveal animation for a drawn spread.

The static spread photo answers "what did I draw"; the animation answers "did
something just happen". Cards rise into place and flip over one at a time, so
the reading opens as a threshold moment instead of three images appearing at
once — the ritual pacing the competitor research asked for.

Two decisions are load-bearing:

* **One shared palette.** Quantising every frame adaptively on its own is ~10x
  slower and lets colours drift between frames, which the eye reads as flicker on
  the dark gradient.
* **Type is drawn after quantisation.** The clip only has room for a few dozen
  palette entries and the card artwork claims most of them, which remaps the
  small captions onto a neighbouring gold and loses the brand colour. Drawing on
  the palette image keeps every caption in its exact token colour, crisper than
  dithered type, and identical in every frame.

The card back is drawn procedurally rather than shipped as an asset: the deck in
``assets/cards`` contains faces only. Frame geometry comes from
:func:`bot.visual.render.spread_card_slots`, so a card can never sit in a
different place in the GIF than in the photo.

Every failure path returns ``None``: the caller then sends the still image, which
is the primary artifact.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageDraw

from . import tokens as T
from .assets import card_image_path
from .render import (
    _asset_background,
    _center_x,
    _center_x_in,
    _font,
    _paste_overlay,
    _sanitize_text,
    _shade_region,
    spread_card_slots,
)

# A card tile is drawn once per card on a transparent canvas, then animated by
# moving and squashing that single tile. Rebuilding it per frame would repeat the
# setup work for every frame of the GIF.
#
# The tile spans the card plus a one-matte margin, and the face sits at the same
# offset inside it that ``render._place_card`` uses. Pasting the tile at
# ``(x - TILE_MARGIN, y - TILE_MARGIN)`` therefore lands the face on exactly the
# pixels the still renderer uses — otherwise the cards drift out of register and
# cover the position captions.
TILE_MARGIN = T.CARD_MATTE_PADDING


@dataclass(frozen=True)
class _Label:
    """Caption geometry for one card, already in output-pixel coordinates."""

    x: int
    y: int
    w: int
    h: int
    position: str
    name: str
    reversed_note: str


def _new_tile(w: int, h: int) -> Image.Image:
    """Transparent tile hosting one card plus its matte margin."""
    return Image.new("RGBA", (w + 2 * TILE_MARGIN, h + 2 * TILE_MARGIN), (0, 0, 0, 0))


def _card_back(w: int, h: int) -> Image.Image:
    """Draw a face-down card: deep panel, gold rule, crescent mark."""
    tile = _new_tile(w, h)
    draw = ImageDraw.Draw(tile)
    m = TILE_MARGIN
    draw.rounded_rectangle(
        [0, 0, tile.width - 1, tile.height - 1], radius=T.CARD_MATTE_RADIUS,
        fill=T.ANIM_BACK_FILL, outline=T.ANIM_BACK_OUTLINE, width=T.CARD_MATTE_WIDTH,
    )
    draw.rounded_rectangle(
        [m + T.CARD_INSET, m + T.CARD_INSET, m + w - 1 - T.CARD_INSET, m + h - 1 - T.CARD_INSET],
        radius=T.ANIM_BACK_INNER_RADIUS, outline=T.ANIM_BACK_OUTLINE, width=T.CARD_MATTE_WIDTH,
    )
    cx, cy, radius = tile.width // 2, tile.height // 2, T.ANIM_BACK_MARK_RADIUS
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline=T.ANIM_BACK_MARK, width=T.CARD_MATTE_WIDTH,
    )
    # Crescent: shift a disc over the ring so the mark reads as a moon.
    draw.ellipse(
        [cx - radius + radius // 2, cy - radius, cx + radius + radius // 2, cy + radius],
        fill=T.ANIM_BACK_FILL,
    )
    return tile


def _card_face(card, w: int, h: int, reversed_: bool) -> Image.Image | None:
    """Render one card onto a transparent tile, or None when the asset is missing."""
    path = card_image_path(card)
    if path is None:
        return None
    try:
        face = Image.open(path).convert("RGB")
    except (OSError, ValueError):
        return None
    if reversed_:
        face = face.rotate(180)
    tile = _new_tile(w, h)
    draw = ImageDraw.Draw(tile)
    m = TILE_MARGIN
    draw.rounded_rectangle(
        [0, 0, tile.width - 1, tile.height - 1], radius=T.CARD_MATTE_RADIUS,
        fill=T.CARD_MATTE_FILL, outline=T.CARD_MATTE_OUTLINE, width=T.CARD_MATTE_WIDTH,
    )
    inset = T.CARD_INSET
    tile.paste(face.resize((w - inset * 2, h - inset * 2), Image.LANCZOS), (m + inset, m + inset))
    outline = T.CARD_FRAME_REVERSED_OUTLINE if reversed_ else T.CARD_FRAME_OUTLINE
    draw.rounded_rectangle(
        [m, m, m + w - 1, m + h - 1], radius=T.CARD_FRAME_RADIUS,
        outline=outline, width=T.CARD_FRAME_WIDTH,
    )
    return tile


def _squash(tile: Image.Image, factor: float) -> Image.Image:
    """Squeeze a tile horizontally to fake the turning of a card."""
    return tile.resize((max(2, int(tile.width * factor)), tile.height), Image.LANCZOS)


def _dither() -> Image.Dither:
    return getattr(Image.Dither, T.ANIM_DITHER.upper(), Image.Dither.FLOYDSTEINBERG)


def _base_frame(spread_title: str) -> Image.Image:
    """Render the atmosphere only: background plate, readability shade, sigil."""
    W, H = T.CANVAS_SPREAD
    base = _asset_background("moira_altar_portrait.jpg", W, H, seed=len(spread_title))
    _shade_region(base, T.SPREAD_TOP_SHADE)
    _paste_overlay(base, "moira_sigil_clean.png", 150, 150, (W // 2, H - 150))
    return base


def _reveal_schedule(card_count: int) -> list[list[int]]:
    """Which cards have settled, per frame. Mirrors the build loop in order."""
    per_card = 1 + len(T.ANIM_FLIP_WIDTHS) + 1
    schedule: list[list[int]] = [[]]
    for index in range(card_count):
        schedule.extend([[index]] * (per_card - 1))
        schedule.append(list(range(index + 1)))
    schedule.extend([list(range(card_count))] * T.ANIM_HOLD_FRAMES)
    return schedule


def make_spread_animation(
    spread_title: str, cards_info: list[dict], footer: str = "MOIRA", lang: str = "ru"
) -> bytes | None:
    """Return GIF bytes revealing the drawn cards, or None when it cannot be built.

    ``cards_info`` matches :func:`bot.visual.render.make_spread_image`. A single
    card is not animated — there is no sequence to stage — so the caller should
    fall back to the still image.
    """
    drawn = cards_info[:3]
    if len(drawn) < 2:
        return None

    try:
        width = T.ANIM_CANVAS_WIDTH
        scale = width / T.CANVAS_SPREAD[0]
        height = round(T.CANVAS_SPREAD[1] * scale)

        base = _base_frame(spread_title)
        slots = spread_card_slots(len(drawn))
        reversed_note = T.REVERSED_NOTE.get(lang, "reversed")

        tiles = [
            _card_face(info["card"], slot[2], slot[3], bool(info.get("reversed")))
            or _card_back(slot[2], slot[3])
            for info, slot in zip(drawn, slots, strict=False)
        ]
        backs = [_card_back(slot[2], slot[3]) for slot in slots]

        def compose(placed: list[tuple[int, int, Image.Image]]) -> Image.Image:
            frame = base.copy()
            for x, y, tile in placed:
                frame.paste(tile, (x, y), tile)
            return frame.resize((width, height), Image.LANCZOS)

        frames: list[Image.Image] = [compose([])]
        durations: list[int] = [T.ANIM_FRAME_MS]
        placed: list[tuple[int, int, Image.Image]] = []

        for (x, y, _w, _h), tile, back in zip(slots, tiles, backs, strict=True):
            # The back of this card slides up into the slot, still translucent.
            incoming = tile.copy()
            incoming.putalpha(int(255 * T.ANIM_SLIDE_ALPHA))
            placed.append((x - TILE_MARGIN, y - TILE_MARGIN + T.ANIM_SLIDE_PX, incoming))
            frames.append(compose(placed))
            durations.append(T.ANIM_FRAME_MS)

            # The flip: the face narrows, the back shows at the midpoint, face returns.
            for step, factor in enumerate(T.ANIM_FLIP_WIDTHS):
                squashed = _squash(back if step == 1 else tile, factor)
                placed[-1] = (
                    x - TILE_MARGIN + (tile.width - squashed.width) // 2,
                    y - TILE_MARGIN,
                    squashed,
                )
                frames.append(compose(placed))
                durations.append(T.ANIM_FRAME_MS)

            placed[-1] = (x - TILE_MARGIN, y - TILE_MARGIN, tile)
            frames.append(compose(placed))
            durations.append(T.ANIM_FRAME_MS)

        for _ in range(T.ANIM_HOLD_FRAMES):
            frames.append(compose(placed))
            durations.append(T.ANIM_HOLD_MS)

        palette = frames[-1].quantize(
            colors=T.ANIM_COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
        )
        title_font = _font(round(T.FONT_SPREAD_TITLE * scale), bold=True)
        foot_font = _font(round(T.FONT_SPREAD_FOOTER * scale))
        pos_font = _font(round(T.FONT_SPREAD_POSITION * scale))
        name_font = _font(round(T.FONT_SPREAD_NAME * scale), bold=True)
        note_font = _font(round(T.FONT_SPREAD_NOTE * scale))

        labels = [
            _Label(
                round(x * scale), round(y * scale), round(w * scale), round(h * scale),
                _sanitize_text(info["label"]), _sanitize_text(info["name"]),
                reversed_note if info.get("reversed") else "",
            )
            for info, (x, y, w, h) in zip(drawn, slots, strict=True)
        ]

        quantised: list[Image.Image] = []
        for frame, revealed in zip(frames, _reveal_schedule(len(drawn)), strict=True):
            indexed = frame.quantize(palette=palette, dither=_dither())
            draw = ImageDraw.Draw(indexed)
            title = _sanitize_text(spread_title)
            draw.text((_center_x(draw, width, title, title_font), round(T.SPREAD_TITLE_Y * scale)),
                      title, font=title_font, fill=T.TEXT_TITLE)
            foot = _sanitize_text(footer)
            draw.text(
                (_center_x(draw, width, foot, foot_font),
                 round((T.CANVAS_SPREAD[1] + T.SPREAD_FOOTER_OFFSET_Y) * scale)),
                foot, font=foot_font, fill=T.TEXT_FOOTER,
            )
            for label in (labels[i] for i in revealed):
                draw.text(
                    (_center_x_in(draw, label.x, label.w, label.position, pos_font),
                     label.y + round(T.SPREAD_LABEL_OFFSET_Y * scale)),
                    label.position, font=pos_font, fill=T.TEXT_POSITION,
                )
                draw.text(
                    (_center_x_in(draw, label.x, label.w, label.name, name_font),
                     label.y + label.h + round(T.SPREAD_NAME_OFFSET_Y * scale)),
                    label.name, font=name_font, fill=T.TEXT_PRIMARY,
                )
                if label.reversed_note:
                    draw.text(
                        (_center_x_in(draw, label.x, label.w, label.reversed_note, note_font),
                         label.y + label.h + round(T.SPREAD_NOTE_OFFSET_Y * scale)),
                        label.reversed_note, font=note_font, fill=T.TEXT_REVERSED,
                    )
            quantised.append(indexed)

        buf = io.BytesIO()
        quantised[0].save(
            buf, format="GIF", save_all=True, append_images=quantised[1:],
            duration=durations, loop=0, optimize=True, disposal=2,
        )
        return buf.getvalue() or None
    except (OSError, ValueError):
        return None
