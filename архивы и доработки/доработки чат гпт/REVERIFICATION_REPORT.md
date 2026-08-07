# Отчёт перепроверки Moira

Дата: 2026-08-07.

## Среда проверки

Исходный ZIP не содержал Windows `.venv`, указанную в ТЗ. Sandbox: Linux,
Python 3.13.5, pytest 9.0.2. В sandbox отсутствуют `aiogram`, `aiosqlite`,
`edge-tts`, `instructor`, `posthog`; публичный PyPI из среды недоступен.

Поэтому проверки разделены на два уровня:

1. **Реальный production-код без внешних сервисов** — deck, fallback, Pillow,
   content cases, Pydantic-схема, integration smoke, compileall. Эти проверки
   выполнялись без подмен production-модулей.
2. **Полный legacy pytest/import** — выполнен с внешними test-only shim для
   отсутствующих `aiogram`/`aiosqlite`. Shim лежит вне проекта и не попадает в
   выдаваемый архив. Это проверяет регрессии кода, но не заменяет финальный
   прогон в оригинальной Windows `.venv`.

## Результаты тестов

### Синтаксис

```text
$ python -m compileall bot
compileall: OK
```

### Финальный pytest в sandbox с test-only dependency shims

```text
$ PYTHONPATH=/mnt/data/aiogram_shim:/mnt/data/aiosqlite_shim:. python -m pytest tests/ -q
........................................................................ [ 96%]
...                                                                      [100%]
75 passed in 0.28s
```

Итого: **75 passed, 0 failed** при доступных test-only dependency shims.

Без shim полный сбор suite останавливается до запуска тестов:

```text
7 errors during collection
ModuleNotFoundError: No module named 'aiogram'
exit_code=2
```

Это ограничение sandbox/dependency coverage, а не падение тестовой логики.

## Колода

Фактическая проверка `build_deck()`:

```text
deck_count: 78
unique_ids: 78
arcana: {'major': 22, 'minor': 56}
ru missing= 0 upright_equals_reversed= 0
en missing= 0 upright_equals_reversed= 0
DECK CHECK PASSED
```

Дополнительно:

```text
pytest tests/test_cards_78.py -q
10 passed in 0.05s
```

## Fallback

```text
pytest tests/test_fallback.py -q
7 passed in 0.06s
```

Integration smoke получил валидные тексты «Ситуации»:

```text
fallback_ru: OK 517 chars
fallback_en: OK 538 chars
```

В fallback также убрана универсальная фраза «Прислушайтесь…» / `Listen to...`;
practical focus теперь связывает скрытый фактор со следующим шагом.

## Мой Аркан

Проверены все `4^6 = 4096` допустимых векторов ответов. Набор достижимых
результатов:

```text
[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
count: 22
QUIZ 22/22 CHECK PASSED
```

Legacy-проверка:

```text
PATCH 5 TESTS PASSED
```

## Визуал

- создан `bot/visual/tokens.py`;
- `render.py` переведён на design tokens;
- canvas: spread 1080×1080, share/single/altar/quiz 1080×1350;
- добавлены font fitting/wrapping для длинных RU/EN названий;
- missing asset отображается оформленным placeholder;
- project-local font проверен с Liberation Serif (SIL OFL 1.1), fallback остаётся
  работоспособным без бинарного файла;
- `artifacts/visual_review/`: **16/16 PNG**, каждый проверен Pillow;
- `no_font_fallback.png` и `missing_asset.png` проходят graceful degradation.

Полный перечень и размеры: `docs/VISUAL_REVIEW.md`.

## 48 контентных сценариев

`tests/content_cases.json` содержит **48 сценариев**: 8 сценариев × 3 расклада ×
RU/EN. Матрица включает upright, reversed, mixed, несколько Major Arcana,
повтор масти, конфликтующие карты, эмоциональные и нейтральные вопросы.

```text
$ python -m pytest tests/test_content_cases.py -v
collected 49 items
...
49 passed in 0.07s
```

49-й тест проверяет форму самой матрицы; все **48/48 сценариев** прошли.

## LLM-схема

Добавлены реальные ограничения Pydantic:

- `headline`: ≤90;
- `opening`: 120–250;
- content каждой `card_interpretation`: 300–550 суммарно;
- `synthesis`: 500–900;
- `practical_focus`: 180–350;
- `reflection_question`: ≤220;
- `voice_summary`: 500–800;
- `share_summary`: 180–300.

Дополнительно schema validator запрещает почти дословную копию `synthesis` в
`voice_summary`; `interpret_reading()` отбрасывает ответ, если `share_summary`
дословно повторяет приватный вопрос пользователя.

```text
pytest tests/test_llm_schema_lengths.py -q
9 passed in 0.17s
```

Исправлена EN-ориентация reversed в prompt и устранён module-global
`_current_spread_id`.

## Интеграционный smoke

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

Подробности: `docs/INTEGRATION_SMOKE.md`.

## Стабилизационные executable-тесты

С внешними test-only dependency shims:

```text
ALL SMOKE TESTS PASSED
PATCH 1 TESTS PASSED
PATCH 2 TESTS PASSED
PATCH 3 TESTS PASSED
PATCH 4 CRITICAL TESTS PASSED
PATCH 5 TESTS PASSED
PATCH 6 TESTS PASSED
```

Сообщения `PostHog init failed`, `audio fallback failed` и simulated Telegram
error являются ожидаемыми ветвями самих тестов; тесты завершились успешно.

## Расхождения с предыдущим отчётом / исходным ТЗ

1. Фраза в ТЗ «бот никогда не запускался end-to-end, только импорты» устарела:
   в приложенном `bot.log` есть реальные запуски Telegram polling и обработанные
   updates. Новый offline integration smoke всё равно был добавлен, поскольку он
   проверяет воспроизводимые функции без сети.
2. Визуальная галерея действительно была неполной; теперь обязательных файлов 16.
3. `tests/content_cases.json` и `tests/test_content_cases.py` отсутствовали; теперь
   созданы и проходят.
4. Ограничения длины LLM были только инструкцией в prompt/частично схемой; теперь
   критические диапазоны закреплены Pydantic-валидацией.
5. В EN card block найден реальный дефект локализации reversed; исправлен.

## Что требует ручной проверки

- финальный `./.venv/Scripts/python.exe -m pytest tests/ -q` в исходной Windows
  `.venv` с реальными зависимостями;
- polling с реальным Telegram-токеном;
- реальный звук edge-tts и отправка voice/audio;
- реальные ответы LLM после ужесточения схемы;
- отрисовка на телефоне;
- восприятие RU/EN пользователями;
- добавление/проверка project-local Liberation Serif в production-пакете, если
  требуется полностью идентичная типографика на разных ОС.
