# Integration smoke Moira

Дата: 2026-08-07.

## Среда и важное ограничение

Загруженный архив проекта не содержит исходную Windows `.venv`. Sandbox работает
на Python 3.13.5, а публичный PyPI из среды недоступен. Поэтому `aiogram` и
`aiosqlite` нельзя было установить в sandbox. Проверки ядра ниже выполнены на
реальном production-коде без сети; импорт `bot.main` и старые тесты, которым
нужен aiogram/aiosqlite, дополнительно прогнаны с **внешними test-only shims**,
расположенными вне проекта. Эти shims не входят в исходники и не входят в
выдаваемый архив.

Это означает: функциональный smoke ядра подтверждён, но финальный запуск полного
suite в оригинальной `C:/Users/IMYAREK/Voprosy/moira/.venv` нужно повторить на
Windows.

## 1. Импорты

Синтаксическая проверка production-кода:

```text
python -m compileall bot
```

Статус: ✅ — все модули компилируются.

Прямой `from bot.main import *` без shim в sandbox: ❌ environment blocker —
`ModuleNotFoundError: No module named 'aiogram'`.

С внешним test-only aiogram shim:

```text
All imports OK (sandbox aiogram shim)
```

Статус production-зависимостей: ⚠️ требуется повтор в исходной Windows `.venv`.

## 2. End-to-end функции без сети/LLM

Команда:

```text
python tests/integration_smoke_core.py
```

Фактический вывод:

```text
fallback_ru: OK 517 chars
fallback_en: OK 538 chars
make_spread_image: OK 1080x1080 244127 bytes
make_share_image: OK 1080x1350 211644 bytes
make_single_image upright: OK 1080x1350 171771 bytes
make_single_image reversed: OK 1080x1350 171941 bytes
quiz.compute_result: OK [12, 4, 2, 19, 10]
voice_summary schema: OK separate field, 500 chars
voice_summary routing: OK reading.py -> voice_text -> synthesize_reading_voice
mock TTS dry-run: OK 5001 bytes
CORE INTEGRATION SMOKE PASSED
```

Статусы:

| Проверка | Статус |
|---|---|
| `build_deck()` → 3 карты → fallback «Ситуация» RU | ✅ |
| то же EN | ✅ |
| `make_spread_image()` | ✅ |
| `make_share_image()` | ✅ |
| `make_single_image()` upright | ✅ |
| `make_single_image()` reversed | ✅ |
| `quiz.compute_result()` ×5 | ✅ |
| `voice_summary` — отдельное поле схемы | ✅ |
| `voice_summary` маршрутизируется в TTS | ✅ |
| TTS dry-run с mock `edge_tts` | ✅ |

## 3. Голосовая ветка

`bot/handlers/reading.py` формирует `voice_text` из `result.headline` +
`result.voice_summary`, а затем передаёт именно `voice_text` в
`synthesize_reading_voice(...)`. Основной `synthesis` вместо него не используется.

Dry-run не вызывает сеть: модуль `edge_tts` подменяется локальным mock,
возвращающим два audio-chunk общей длиной 5001 byte. Проверка прошла.

## 4. Обнаруженная и исправленная интеграционная ошибка

В `_build_card_block()` ориентация reversed в EN могла попасть в prompt как
русское `перевёрнутая` из-за неоднозначного условного выражения. Логика
переписана на явные ветви RU/EN; отдельная проверка получила `reversed` для EN.

Также убран module-global `_current_spread_id`: `spread_id` теперь передаётся в
`_build_card_block()` явно, что исключает взаимное влияние параллельных раскладов.

## 5. Что не проверено реальным внешним сервисом

- реальный polling Telegram с токеном;
- реальная отправка voice/audio конкретному Telegram-пользователю;
- реальный запрос edge-tts;
- реальный LLM API ответ по новой Pydantic-схеме.

Эти пункты требуют ручной/production проверки и не маскируются как пройденные.
