"""Invite QR on shareable cards.

A shared card must keep working as a signup after it leaves the chat, so the
referral link is rendered as a scannable QR next to the art. These tests pin the
contract: the block appears only when a link exists, it lands on the token
coordinates, and the pixels inside the panel are exactly the QR for that link.
"""
from __future__ import annotations

import builtins
import io
import sys

import pytest
from PIL import Image

from bot.tarot.deck import build_deck
from bot.visual import tokens as T
from bot.visual.render import (
    _paste_qr_invite,
    make_share_image,
    make_single_image,
    qr_code_bytes,
)

LINK = "https://t.me/moira_oracle?start=ref_42_a"


def _card() -> object:
    return build_deck()[0]


def _cards_info() -> list[dict]:
    deck = build_deck()
    return [
        {"label": f"Card {i}", "card": deck[i], "reversed": bool(i % 2), "name": deck[i].name("en")}
        for i in range(3)
    ]


def _crop_code(card: Image.Image, link: str, slot: int, origin: tuple[int, int]) -> Image.Image:
    """Cut the rendered QR back out of a card, mirroring the centering rule."""
    code = Image.open(io.BytesIO(qr_code_bytes(link, size=slot) or b"")).convert("RGB")
    x, y = origin
    code_x = x + (slot - code.width) // 2
    code_y = y + (slot - code.height) // 2
    return card.convert("RGB").crop((code_x, code_y, code_x + code.width, code_y + code.height)), code


def _assert_code_matches(card: Image.Image, link: str, slot: int, origin: tuple[int, int]) -> None:
    actual, expected = _crop_code(card, link, slot, origin)
    assert actual.size == expected.size
    # The card is JPEG-compressed, so compare with a tolerance, not exact bytes.
    mismatch = sum(
        1
        for got, want in zip(actual.tobytes(), expected.tobytes(), strict=False)
        if abs(got - want) > T.QR_MATCH_TOLERANCE
    )
    assert mismatch / len(expected.tobytes()) < 0.02


def test_qr_code_bytes_encodes_a_link() -> None:
    data = qr_code_bytes(LINK)
    assert data is not None
    image = Image.open(io.BytesIO(data))
    assert image.width == image.height > 0
    assert len({c for _, c in image.getcolors(maxcolors=1 << 16) or []}) == 2


@pytest.mark.parametrize(
    "link",
    [
        "https://t.me/moira?start=ref_1_a",
        "https://t.me/moira_oracle?start=ref_42_a",
        "https://t.me/moira_tarot_oracle_bot?start=ref_1234567890_b",
    ],
)
def test_qr_uses_whole_modules_for_realistic_payloads(link: str) -> None:
    """Sharp module edges are what make the code scannable after JPEG."""
    import segno

    code = segno.make(link, error=T.QR_ERROR_LEVEL)
    modules = code.symbol_size(scale=1, border=0)[0] + 2 * T.QR_BORDER
    image = Image.open(io.BytesIO(qr_code_bytes(link, size=160) or b""))
    scale = image.width // modules
    assert scale >= 3, "a slot this small would leave fewer than 3 px per module"
    assert image.width == modules * scale
    assert image.width <= 160


def test_qr_code_bytes_is_none_without_a_link() -> None:
    assert qr_code_bytes("") is None


def test_qr_degrades_when_the_encoder_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing optional dependency must not break the card."""
    real_import = builtins.__import__

    def blocked(name: str, *args, **kwargs):
        if name == "segno":
            raise ImportError("segno is not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    monkeypatch.delitem(sys.modules, "segno", raising=False)
    assert qr_code_bytes(LINK) is None
    # The card still renders, just without the invite block.
    image = Image.open(io.BytesIO(make_share_image("Choice", _cards_info(), "summary", qr_link=LINK)))
    assert image.size == T.CANVAS_SHARE


def test_share_card_contains_the_exact_qr_for_the_referral_link() -> None:
    card = Image.open(
        io.BytesIO(
            make_share_image(
                "Choice", _cards_info(), "A small step.", "Moira", "en",
                LINK, "Scan to get your own reading",
            )
        )
    )
    assert card.size == T.CANVAS_SHARE
    _assert_code_matches(card, LINK, T.SHARE_QR_SIZE, T.SHARE_QR_XY)


def test_share_card_without_a_link_has_no_qr_panel() -> None:
    plain = Image.open(io.BytesIO(make_share_image("Choice", _cards_info(), "A small step.")))
    x, y = T.SHARE_QR_XY
    center = plain.convert("RGB").getpixel((x + T.SHARE_QR_SIZE // 2, y + T.SHARE_QR_SIZE // 2))
    # The night-sky background stays dark where the light invite panel would be.
    assert sum(center) < 300


def test_invite_band_does_not_collide_with_the_summary_block() -> None:
    """The summary text must stop above the invite panel with breathing room."""
    summary_bottom = (
        T.SHARE_SUMMARY_Y
        + (T.SHARE_SUMMARY_MAX_LINES - 1) * T.SHARE_SUMMARY_STEP
        + T.SHARE_SUMMARY_LINE_HEIGHT
    )
    panel_top = T.SHARE_QR_XY[1] - T.QR_PANEL_PAD
    assert panel_top - summary_bottom >= T.QR_BAND_MIN_GAP
    assert panel_top + 2 * T.QR_PANEL_PAD + T.SHARE_QR_SIZE <= T.CANVAS_SHARE[1]


def test_invite_band_does_not_collide_with_the_arcana_subtitle() -> None:
    subtitle_bottom = (
        T.SINGLE_CARDS_Y
        + T.SINGLE_CARD_SIZE[1]
        + T.SINGLE_SUBTITLE_OFFSET_Y
        + (T.SINGLE_SUBTITLE_MAX_LINES - 1) * T.SINGLE_SUBTITLE_STEP
        + T.SINGLE_SUBTITLE_LINE_HEIGHT
    )
    panel_top = T.SINGLE_QR_XY[1] - T.QR_PANEL_PAD
    assert panel_top - subtitle_bottom >= T.QR_BAND_MIN_GAP
    assert panel_top + 2 * T.QR_PANEL_PAD + T.SINGLE_QR_SIZE <= T.CANVAS_SINGLE[1]


def test_arcana_card_carries_its_own_invite_qr() -> None:
    card = Image.open(
        io.BytesIO(
            make_single_image(
                "Your Arcana is The Fool!", "Curious beginning", _card(), "Moira", False, "en",
                LINK, "Find your Arcana for free",
            )
        )
    )
    assert card.size == T.CANVAS_SINGLE
    _assert_code_matches(card, LINK, T.SINGLE_QR_SIZE, T.SINGLE_QR_XY)


def test_altar_card_is_unchanged_without_a_link() -> None:
    """The daily altar is private, so it must never grow an invite block."""
    image = Image.open(
        io.BytesIO(make_single_image("Moira", "The Fool", _card(), "MOIRA", False, "en"))
    )
    x, y = T.SINGLE_QR_XY
    assert sum(image.convert("RGB").getpixel((x + 40, y + 40))) < 300


def test_paste_qr_invite_reports_whether_it_drew() -> None:
    image = Image.new("RGB", (600, 400), (10, 6, 22))
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    assert _paste_qr_invite(image, draw, LINK, "label", 20, 20, 120, 300) is True
    assert _paste_qr_invite(image, draw, "", "label", 20, 20, 120, 300) is False


def test_qr_label_is_localised_in_both_locales() -> None:
    from bot.i18n import t

    for lang in ("ru", "en"):
        label = t(lang, "qr_invite_label")
        quiz_label = t(lang, "qr_invite_label_quiz")
        assert label and label != "qr_invite_label"
        assert quiz_label and quiz_label != "qr_invite_label_quiz"
        assert label != quiz_label
