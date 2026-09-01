"""Render representative Moira visuals into docs/visual_smoke_outputs.

Run explicitly with ``python scripts/visual_smoke.py``. Rendering is intentionally
guarded by ``__main__`` so that importing this module (for example during a
package import scan or test collection) never rewrites the tracked sample
artifacts and never dirties the release tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot.tarot.deck import build_deck
from bot.visual.render import make_share_image, make_single_image, make_spread_image

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "visual_smoke_outputs"


def _build_samples() -> tuple[list[dict], list[dict]]:
    """Return the RU and EN spread definitions used for the smoke render."""
    by_id = {card.id: card for card in build_deck()}
    chosen = [by_id["major_0"], by_id["major_11"], by_id["major_21"]]

    info_ru = [
        {"label": "Суть", "card": chosen[0], "reversed": False, "name": chosen[0].name_ru},
        {"label": "Тень", "card": chosen[1], "reversed": True, "name": chosen[1].name_ru},
        {"label": "Шаг", "card": chosen[2], "reversed": False, "name": chosen[2].name_ru},
    ]
    info_en = [
        {"label": "Essence", "card": chosen[0], "reversed": False, "name": chosen[0].name_en},
        {"label": "Shadow", "card": chosen[1], "reversed": True, "name": chosen[1].name_en},
        {"label": "Next step", "card": chosen[2], "reversed": False, "name": chosen[2].name_en},
    ]
    return info_ru, info_en


def render(output_dir: Path | None = None) -> list[Path]:
    """Render every smoke sample and return the written file paths."""
    out = output_dir or OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    info_ru, info_en = _build_samples()
    # The Shadow position is deliberately reversed in both locales so the
    # reversed-card marker stays covered by the EN sample as well.
    shadow = info_ru[1]["card"]

    written = []
    targets = {
        "spread_ru.jpg": make_spread_image("Три нити момента", info_ru, lang="ru"),
        "spread_en.jpg": make_spread_image("Three threads of the moment", info_en, lang="en"),
        "share_ru.jpg": make_share_image(
            "Три нити момента",
            info_ru,
            "Здесь есть направление, которое стоит заметить.",
            lang="ru",
        ),
        "single_reversed.jpg": make_single_image(
            "Карта дня",
            "Заметь паузу, прежде чем действовать.",
            shadow,
            reversed_=True,
            lang="ru",
        ),
    }
    for name, payload in targets.items():
        path = out / name
        path.write_bytes(payload)
        written.append(path)
    return written


def main() -> None:
    written = render()
    print("generated", sorted(path.name for path in written))


if __name__ == "__main__":
    main()
