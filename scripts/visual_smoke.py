from pathlib import Path

from bot.tarot.deck import build_deck
from bot.visual.render import make_share_image, make_single_image, make_spread_image

root = Path(__file__).resolve().parents[1]
out = root / "docs" / "visual_smoke_outputs"
out.mkdir(exist_ok=True)
cards = build_deck()
by_id = {card.id: card for card in cards}
chosen = [by_id["major_0"], by_id["major_11"], by_id["major_21"]]
info_ru = [
    {"label": "Суть", "card": chosen[0], "reversed": False, "name": chosen[0].name_ru},
    {"label": "Тень", "card": chosen[1], "reversed": True, "name": chosen[1].name_ru},
    {"label": "Шаг", "card": chosen[2], "reversed": False, "name": chosen[2].name_ru},
]
info_en = [
    {"label": "Essence", "card": chosen[0], "reversed": False, "name": chosen[0].name_en},
    {"label": "Shadow", "card": chosen[1], "reved": True, "name": chosen[1].name_en},
    {"label": "Next step", "card": chosen[2], "reversed": False, "name": chosen[2].name_en},
]
(out / "spread_ru.jpg").write_bytes(make_spread_image("Три нити момента", info_ru, lang="ru"))
(out / "spread_en.jpg").write_bytes(make_spread_image("Three threads of the moment", info_en, lang="en"))
(out / "share_ru.jpg").write_bytes(make_share_image("Три нити момента", info_ru, "Здесь есть направление, которое стоит заметить.", lang="ru"))
(out / "single_reversed.jpg").write_bytes(make_single_image("Карта дня", "Заметь паузу, прежде чем действовать.", chosen[1], reversed_=True, lang="ru"))
print("generated", sorted(path.name for path in out.glob("*.jpg")))
