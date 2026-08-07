# Финальный отчёт Moira

Дата: 2026-08-07.

## Сводка

Фаза закрывает внутреннюю часть Moira, указанную в ТЗ: визуальную систему,
контентные регрессии, offline integration smoke, выборочный аудит карт и
ограничения структурированного LLM-ответа.

Главный результат:

- визуал перестал быть набором hardcoded Pillow-констант: добавлены design tokens;
- создана и программно проверена галерея **16/16** обязательных изображений;
- добавлены **48/48** детерминированных контентных сценариев RU/EN;
- добавлен offline integration smoke для fallback/visual/quiz/voice;
- выборочно отредактирован контент Major/Minor Arcana, где были кальки, клише или
  слишком предсказательные формулировки;
- LLM output schema получила реальные ограничения длины и проверки разделения
  public/voice content;
- исправлен отдельный EN-баг reversed orientation и убрано глобальное состояние
  spread id.

Стабилизационные исправления, схема БД, платежи, referral, deployment и языковой
набор не откатывались и намеренно не перерабатывались.

## Результаты тестов

### Production-core без сети

- `compileall bot` — ✅;
- колода — **78 cards, 78 unique IDs, 22 major + 56 minor**, RU/EN без пустых
  meanings, upright/reversed различаются — ✅;
- `test_cards_78.py` — **10 passed**;
- `test_fallback.py` — **7 passed**;
- `test_content_cases.py` — **49 passed** (48 cases + 1 matrix invariant);
- `test_llm_schema_lengths.py` — **9 passed**;
- `integration_smoke_core.py` — ✅;
- `generate_visual_review.py` — **16/16 PNG validated**;
- quiz exhaustive reachability — **22/22 Arcana**.

### Полный pytest

В sandbox исходная Windows `.venv` отсутствует. Без дополнительных зависимостей
suite не собирается из-за отсутствующего `aiogram` (`7 errors during collection`).
С внешними test-only `aiogram`/`aiosqlite` shims, которые **не входят в проект**:

```text
75 passed in 0.28s
```

То есть в проверяемой логике: **75 passed, 0 failed**. Но это не выдаётся за
эквивалент финального запуска в вашей реальной Windows `.venv`.

## Интеграционный smoke

| Пункт | Результат |
|---|---|
| fallback Situation RU | ✅ 517 chars |
| fallback Situation EN | ✅ 538 chars |
| spread image | ✅ 1080×1080 |
| share image | ✅ 1080×1350 |
| single upright | ✅ 1080×1350 |
| single reversed | ✅ 1080×1350 |
| quiz ×5 | ✅ outputs 0–21 |
| `voice_summary` отдельное поле | ✅ |
| `voice_summary` идёт в TTS | ✅ |
| mock TTS без сети | ✅ 5001 bytes |

Подробнее: `docs/INTEGRATION_SMOKE.md`.

## Аудит контента

### Основная выборка Major Arcana

Проверены и отредактированы:

1. `major_1` — Маг / The Magician;
2. `major_10` — Колесо Фортуны / Wheel of Fortune;
3. `major_11` — Справедливость / Justice;
4. `major_14` — Умеренность / Temperance;
5. `major_13` — Смерть / Death.

Исправлялись кальки и универсально-предсказательные конструкции вроде «удачный
цикл», «баланс восторжествует», `golden mean`, `old ends to make way for new`.
Новые тексты описывают наблюдаемую динамику/критерий размышления, не обещая исход.

### Основная выборка Minor Arcana

Проверены и отредактированы:

1. `wands_king` — Король Жезлов / King of Wands;
2. `swords_eight` — Восьмёрка Мечей / Eight of Swords;
3. `swords_five` — Пятёрка Мечей / Five of Swords;
4. `pentacles_six` — Шестёрка Пентаклей / Six of Pentacles;
5. `wands_two` — Двойка Жезлов / Two of Wands.

Убраны/переписаны кальки и неестественные обороты вроде «тирания энтузиазма»,
«пелена спадает с глаз», «между давать и получать», избыточно общий язык.

### Дополнительный sanity-sample Minor Arcana

При повторной случайной проверке выявлены и также исправлены ещё пять карт:

- `pentacles_page` — Паж Пентаклей / Page of Pentacles;
- `swords_three` — Тройка Мечей / Three of Swords;
- `cups_five` — Пятёрка Кубков / Five of Cups;
- `cups_ten` — Десятка Кубков / Ten of Cups;
- `wands_five` — Пятёрка Жезлов / Five of Wands.

В частности исправлена фактическая/образная неточность Five of Cups: в RWS три
кубка опрокинуты, два остаются стоять; прежний текст ошибочно говорил «из трёх
кубков два стоят». Убраны клише `place in the sun`, безусловное «семейное
счастье», автоматический «шанс восстановить» и другие формулы, которые звучали
как предсказание вместо интерпретации.

После последних правок:

```text
pytest tests/test_cards_78.py tests/test_fallback.py tests/test_content_cases.py -q
66 passed
```

Важно: это **выборочный**, а не полный литературный аудит всех 78×RU/EN×2
трактовок. Полный контент-аудит потребовал бы отдельного прохода всей колоды.

## LLM-схема

В `bot/llm/adapter.py` закреплены диапазоны из ТЗ непосредственно Pydantic:

| Поле | Ограничение |
|---|---:|
| headline | 1–90 |
| opening | 120–250 |
| card interpretation content | 300–550 суммарно |
| synthesis | 500–900 |
| practical_focus | 180–350 |
| reflection_question | 1–220 |
| voice_summary | 500–800 |
| share_summary | 180–300 |

`voice_summary` дополнительно проверяется на почти дословное совпадение с
`synthesis` (threshold 0.92). `share_summary` отбрасывается, если дословно
повторяет приватный вопрос пользователя. Эти правила также продублированы в
RU/EN format prompt, чтобы не полагаться только на post-validation.

## Визуальная система

Создан `bot/visual/tokens.py` и переработан `bot/visual/render.py`:

- единая палитра;
- размеры canvas, cards, gaps, typography и atmospheric effects;
- wrapping/font-fit длинных названий;
- project-local → OS → emergency font fallback;
- designed placeholder для отсутствующей картинки карты;
- одинаковые принципы RU/EN.

Галерея и точные размеры — `docs/VISUAL_REVIEW.md`.

Во время проверки использовался Liberation Serif (SIL OFL 1.1). Бинарные font
файлы намеренно не включаются в выдаваемый ZIP; лицензия и инструкция остаются в
`assets/fonts/`. Без них рендерер работает через системный fallback.

## Список созданных/изменённых файлов этой фазой

### Production code

- `bot/visual/tokens.py` — новый;
- `bot/visual/render.py` — переработан;
- `bot/llm/adapter.py` — schema/localization/concurrency fixes;
- `bot/tarot/data_major.py` — выборочные RU/EN content fixes;
- `bot/tarot/data_minor.py` — выборочные RU/EN content fixes;
- `bot/tarot/fallback.py` — practical-focus wording.

### Tests / artifacts

- `tests/content_cases.json` — 48 cases;
- `tests/test_content_cases.py` — новый regression runner;
- `tests/test_llm_schema_lengths.py` — schema boundaries;
- `tests/integration_smoke_core.py` — offline integration smoke;
- `tests/generate_visual_review.py` — deterministic gallery generator;
- `artifacts/visual_review/*.png` — 16 обязательных изображений.

### Docs

- `docs/VISUAL_REVIEW.md`;
- `docs/INTEGRATION_SMOKE.md`;
- `docs/REVERIFICATION_REPORT.md`;
- `docs/FINAL_REPORT.md`;
- `assets/fonts/README.md`;
- `assets/fonts/OFL-Liberation.txt`;
- `README.md` — секции визуальной системы и тестов обновлены.

В архиве уже находились другие незакоммиченные изменения (`LICENSE`, `diag.py`,
исследовательские TXT/MD и др.). Они не считаются результатом этой фазы и
намеренно не откатывались.

## Что осталось на ручную проверку

1. В исходной Windows-среде выполнить:

   ```powershell
   ./.venv/Scripts/python.exe -m pytest tests/ -q
   ```

2. Проверить реальный Telegram polling и один полный пользовательский расклад.
3. Проверить реальный edge-tts звук и поведение voice/audio в Telegram.
4. Проверить один реальный LLM RU и EN ответ — новая schema строже прежней, поэтому
   важно убедиться, что выбранная модель стабильно укладывается в диапазоны.
5. Открыть несколько visual-review карточек на телефоне.
6. Для полностью одинаковой типографики между Windows/VPS добавить project-local
   Liberation Serif по путям из `assets/fonts/README.md`.

## Готов ли бот к выкатке?

**С оговорками.** Внутреннее ядро этой фазы прошло воспроизводимые offline-тесты,
48 контентных сценариев, visual regression и schema checks; полный suite с
sandbox dependency shims — 75/75. Подтверждённых регрессий в изменённой логике
после финального прогона нет.

Но выпуск нельзя честно назвать полностью подтверждённым до одного финального
`pytest tests/ -q` в вашей исходной Windows `.venv` и короткого live-smoke
Telegram/LLM/TTS. Это ограничения проверки среды, а не скрытые «зелёные» пункты.
