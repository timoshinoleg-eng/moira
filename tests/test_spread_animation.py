"""Spread reveal animation: geometry, registration with the still image, budget.

The animation's whole value is that it feels like a deliberate threshold moment,
which only holds if the cards land exactly where the still photo puts them and
the clip stays small enough to send. These tests pin both, plus the graceful
degradation the reading flow depends on.
"""
from __future__ import annotations

import io

import pytest
from aiogram.exceptions import TelegramBadRequest
from PIL import Image, ImageSequence

from bot.tarot.deck import build_deck
from bot.visual import tokens as T
from bot.visual.animate import TILE_MARGIN, make_spread_animation
from bot.visual.render import make_spread_image, spread_card_slots

# Telegram's Bot API rejects animations above 10 MB; stay far below it.
TELEGRAM_ANIMATION_LIMIT = 10 * 1024 * 1024


def _cards_info(lang: str = "en", count: int = 3) -> list[dict]:
    deck = build_deck()
    labels = ["PAST", "PRESENT", "FUTURE"]
    return [
        {
            "label": labels[i] if lang == "en" else ["ПРОШЛОЕ", "НАСТОЯЩЕЕ", "БУДУЩЕЕ"][i],
            "card": deck[i],
            "reversed": i == 1,
            "name": deck[i].name(lang),
        }
        for i in range(count)
    ]


def _frames(data: bytes) -> list[Image.Image]:
    image = Image.open(io.BytesIO(data))
    return [frame.convert("RGB").copy() for frame in ImageSequence.Iterator(image)]


def test_animation_is_a_multi_frame_gif_within_the_telegram_limit() -> None:
    data = make_spread_animation("Choice", _cards_info(), "Moira", "en")
    assert data is not None
    assert data[:6] in (b"GIF87a", b"GIF89a")
    assert len(data) < TELEGRAM_ANIMATION_LIMIT


def test_cards_are_revealed_one_at_a_time() -> None:
    frames = _frames(make_spread_animation("Choice", _cards_info(), "Moira", "en") or b"")
    assert len(frames) >= 6
    # A clip where nothing changes is not an animation.
    assert len({f.tobytes() for f in frames}) >= 3


def _first_frame_patch_brightness(frame: Image.Image, slot: tuple[int, int, int, int]) -> float:
    x, y, w, h = slot
    scale = frame.width / T.CANVAS_SPREAD[0]
    patch = frame.crop(
        (int(x * scale), int(y * scale), int((x + w) * scale), int((y + h) * scale))
    )
    raw = patch.convert("L").tobytes()
    return sum(raw) / len(raw)


def _caption_pixels(frame: Image.Image, box: tuple[int, int, int, int], colour: tuple) -> int:
    """Count pixels close to the caption colour inside a scaled box.

    A tolerance is required: the still is JPEG and the clip is a dithered
    64-colour GIF, so the pure token colour never survives either encoder.
    """
    scale = frame.width / T.CANVAS_SPREAD[0]
    patch = frame.crop(
        (int(box[0] * scale), int(box[1] * scale), int(box[2] * scale), int(box[3] * scale))
    ).convert("RGB")
    raw = patch.tobytes()
    return sum(
        1
        for i in range(0, len(raw), 3)
        if all(abs(raw[i + c] - colour[c]) <= T.ANIM_CAPTION_TOLERANCE for c in range(3))
    )


def test_the_first_frame_shows_no_card_yet() -> None:
    """The threshold moment only reads if the spread starts empty."""
    frames = _frames(make_spread_animation("Choice", _cards_info(), "Moira", "en") or b"")
    # An empty slot is the dark night sky, not a bright card face.
    assert _first_frame_patch_brightness(frames[0], spread_card_slots(3)[0]) < 90


def test_position_captions_stay_visible_in_the_settled_frame() -> None:
    """Regression: an offset tile drew card art over the position labels.

    The still renderer and the animation must agree on where a card sits, so the
    label drawn just above each slot has to survive the reveal.
    """
    frames = _frames(make_spread_animation("Choice", _cards_info(), "Moira", "en") or b"")
    settled = frames[-1]
    still = Image.open(
        io.BytesIO(make_spread_image("Choice", _cards_info(), "Moira", "en"))
    ).convert("RGB")
    still_small = still.resize((settled.width, settled.height), Image.LANCZOS)

    for x, y, w, _h in spread_card_slots(3):
        label_box = (x, y + T.SPREAD_LABEL_OFFSET_Y, x + w, y + T.SPREAD_LABEL_OFFSET_Y + 30)
        assert _caption_pixels(settled, label_box, T.TEXT_POSITION) > 20, (
            "position caption is missing from the animation"
        )
        assert _caption_pixels(still_small, label_box, T.TEXT_POSITION) > 20, (
            "control: the still render must show the same caption"
        )


def test_a_single_card_is_not_animated() -> None:
    """There is no sequence to stage, so the caller must keep the still image."""
    assert make_spread_animation("Card of the day", _cards_info(count=1), "Moira", "en") is None


def test_russian_captions_are_animated() -> None:
    data = make_spread_animation("Выбор", _cards_info("ru"), "Мойра", "ru")
    assert data is not None
    assert len(_frames(data)) >= 6


def test_reversed_marker_survives_the_animation() -> None:
    frames = _frames(make_spread_animation("Choice", _cards_info(), "Moira", "en") or b"")
    x, y, w, h = spread_card_slots(3)[1]
    scale = frames[0].width / T.CANVAS_SPREAD[0]
    band = (
        int((x + w * 0.2) * scale),
        int((y + h + T.SPREAD_NAME_OFFSET_Y) * scale),
        int((x + w * 0.8) * scale),
        int((y + h + T.SPREAD_NOTE_OFFSET_Y + 30) * scale),
    )
    patch = frames[-1].crop(band).convert("L")
    # The "reversed" caption is light text on a dark sky.
    assert patch.getextrema()[1] > 120


def test_tile_margin_matches_the_still_renderer() -> None:
    """Guards the registration contract the settled-frame test relies on."""
    assert TILE_MARGIN == T.CARD_MATTE_PADDING


@pytest.mark.parametrize("count", [2, 3])
def test_spreads_of_two_or_three_cards_animate(count: int) -> None:
    data = make_spread_animation("Situation", _cards_info(count=count), "Moira", "en")
    assert data is not None
    assert len(_frames(data)) >= 4


class _FakeMessage:
    """Minimal stand-in for the aiogram Message used by _send_spread."""

    def __init__(self, *, fail_animation: bool = False) -> None:
        self.fail_animation = fail_animation
        self.animations: list[bytes] = []
        self.photos: list[bytes] = []

    async def answer_animation(self, animation, caption=None, **kwargs) -> None:
        if self.fail_animation:
            raise TelegramBadRequest(
                method=None, message="Animation is too big"
            )
        self.animations.append(animation.data)

    async def answer_photo(self, photo, caption=None, **kwargs) -> None:
        self.photos.append(photo.data)


async def _run_send(message, animate: bool) -> str:
    from bot.handlers.reading import _send_spread

    return await _send_spread(
        message,
        spread_title="Choice",
        cards_info=_cards_info(),
        caption="caption",
        lang="en",
        animate=animate,
    )


def test_send_spread_prefers_the_clip() -> None:
    import asyncio

    message = _FakeMessage()
    assert asyncio.run(_run_send(message, animate=True)) == "animation"
    assert message.animations and not message.photos


def test_send_spread_falls_back_to_the_photo_when_disabled() -> None:
    import asyncio

    message = _FakeMessage()
    assert asyncio.run(_run_send(message, animate=False)) == "photo"
    assert message.photos and not message.animations


def test_send_spread_falls_back_when_the_upload_is_rejected() -> None:
    """Telegram refusing the clip must not cost the user their spread."""
    import asyncio

    message = _FakeMessage(fail_animation=True)
    assert asyncio.run(_run_send(message, animate=True)) == "photo"
    assert message.photos


def test_send_spread_never_raises_when_both_artifacts_fail() -> None:
    import asyncio

    class _Broken(_FakeMessage):
        async def answer_photo(self, photo, caption=None, **kwargs) -> None:
            raise RuntimeError("telegram is down")

    assert asyncio.run(_run_send(_Broken(fail_animation=True), animate=True)) == "none"
