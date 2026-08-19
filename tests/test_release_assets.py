from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from bot.tarot.deck import build_deck
from bot.visual import tokens as T
from bot.visual.render import (
    PROJECT_FONTS_DIR,
    VISUAL_PACK_DIR,
    _font,
    _sanitize_text,
    make_share_image,
    make_single_image,
    make_spread_image,
)


REQUIRED_VISUAL_PACK = {
    "moira_altar_portrait.jpg",
    "moira_share_background.jpg",
    "moira_sigil_clean.png",
    "moira_thread_overlay_vector.png",
}


def _cards_info() -> list[dict]:
    cards = build_deck()[:3]
    return [
        {
            "label": f"Позиция {index + 1}",
            "card": card,
            "reversed": index == 1,
            "name": card.name("ru"),
        }
        for index, card in enumerate(cards)
    ]


def _image_size(payload: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(payload)) as image:
        image.verify()
    with Image.open(io.BytesIO(payload)) as image:
        return image.size


def test_required_visual_pack_is_exact_and_readable() -> None:
    found = {path.name for path in VISUAL_PACK_DIR.iterdir() if path.is_file()}
    assert found == REQUIRED_VISUAL_PACK
    for name in REQUIRED_VISUAL_PACK:
        with Image.open(VISUAL_PACK_DIR / name) as image:
            image.verify()


def test_release_fonts_are_project_local_and_support_cyrillic_rendering() -> None:
    regular = _font(32)
    bold = _font(32, bold=True)
    assert Path(regular.path).resolve().parent == PROJECT_FONTS_DIR.resolve()
    assert Path(bold.path).resolve().parent == PROJECT_FONTS_DIR.resolve()
    assert regular.getbbox("Мойра видит тихий порог перемен") is not None
    assert bold.getbbox("Перевёрнутая карта") is not None


def test_missing_glyph_sanitizer_removes_html_and_unsupported_symbols() -> None:
    sanitized = _sanitize_text("<b>Длинный русский заголовок</b> ✦ 🃏 → без квадратов")
    assert sanitized == "Длинный русский заголовок без квадратов"


def test_renderer_accepts_long_cyrillic_and_reversed_card_at_release_dimensions() -> None:
    cards = _cards_info()
    long_title = (
        "Очень длинный русский заголовок расклада о выборе следующего спокойного "
        "и проверяемого шага без обещаний неизбежного будущего"
    )
    summary = (
        "Карты предлагают отделить наблюдаемый факт от предположения, заметить границу "
        "и проверить один небольшой обратимый шаг до окончательного решения."
    )
    spread = make_spread_image(long_title, cards, lang="ru")
    share = make_share_image(long_title, cards, summary, lang="ru")
    single = make_single_image(
        long_title,
        "Перевёрнутая карта показывает внутреннюю задержку и просит не торопить вывод.",
        cards[1]["card"],
        reversed_=True,
        lang="ru",
    )

    assert _image_size(spread) == T.CANVAS_SPREAD
    assert _image_size(share) == T.CANVAS_SHARE
    assert _image_size(single) == T.CANVAS_SINGLE
