# Интеграционный smoke-тест Moira (INTEGRATION_SMOKE)

Дата: 2026-08-07. Среда: Linux-песочница, Python 3.11.15, aiogram 3.30.0, pydantic 2.13.4,
Pillow 12.3.0. Все проверки выполнялись **без сети и без LLM** (fallback-путь и моки).

## 3.1 Проверка импортов
```
python3 -c "import bot.main; import bot.visual.render, bot.visual.tokens; import bot.llm.adapter; import bot.voice.speaker; print('All imports OK')"
```
Результат: ✅ — все модули импортируются (bot.main тянет aiogram-хендлеры, БД, analytics).

## 3.2 End-to-end функции (без сети/LLM)

| Функция | Статус | Вывод |
|---------|--------|-------|
| import bot.main + core modules | ✅ | all modules import cleanly |
| build_deck() | ✅ | 78 cards |
| compose_fallback_reading(ru) | ✅ | headline='Трактовка расклада', plain_len=645 |
| compose_fallback_reading(en) | ✅ | headline='Reading interpretation', plain_len=617 |
| fallback voice_text != plain_text (RU) | ✅ | voice_text is a separate spoken variant |
| make_spread_image() | ✅ | (1080, 1500) RGB 282209 bytes |
| make_share_image() | ✅ | (1080, 1080) RGB 203626 bytes |
| make_single_image(upright) | ✅ | (1080, 1350) RGB 159126 bytes |
| make_single_image(reversed) | ✅ | (1080, 1350) RGB 159122 bytes |
| compute_result() x5 | ✅ | answers -> arcana: [12, 4, 2, 19, 10] |
| voice_summary separate field | ✅ | schema fields: ['headline', 'opening', 'card_interpretations', 'synthesis', 'practical_focus', 'reflection_question', 'voice_summary', 'share_summary'] |
| voice_summary != synthesis (sample) | ✅ | voice=352ch, synthesis=420ch |
| voice dry-run (mock edge-tts) | ✅ | 5004 bytes returned |
| clean_for_speech() | ✅ | 'Привет мир' |
| clean_for_speech() limit | ✅ | MAX_CHARS=1000 |

## 3.3 Голосовая ветка

- `voice_summary` попадает в голосовой текст: `reading.py` собирает TTS как
  `headline + voice_summary` для LLM-пути и отдельный `voice_text` для fallback-пути
  (проверено: `voice_text != plain_text`).
- Dry-run TTS с моком `edge_tts.Communicate` (без сети): `synthesize_reading_voice()`
  возвращает байты MP3 (> 4000 б) — ✅.
- `clean_for_speech()` убирает HTML-теги и эмодзи, обрезает до 1000 символов — ✅.

## 3.4 Команды для воспроизведения

```bash
python -m pytest tests/ -q                                   # весь набор
python -m pytest tests/test_content_cases.py -v              # 48 сценариев
python -c "import bot.main; print('All imports OK')"         # импорты
# smoke-ячейки ноутбука: deck→fallback, make_*_image, compute_result, voice dry-run
```

## Ограничения (ручная проверка)

- Реальный поллинг с Telegram-токеном (нужен `BOT_TOKEN` + сеть) — не проверялся.
- Реальный звук edge-tts (сеть/сервис Microsoft) — не проверялся, только мок.
- Отрисовка изображений на телефоне — ручная проверка.
