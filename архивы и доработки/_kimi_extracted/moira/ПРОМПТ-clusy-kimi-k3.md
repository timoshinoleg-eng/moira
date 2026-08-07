# Moira — финальная доработка: визуал, тесты, интеграция, отчёты

## Кто ты

Ты — senior Python/aiogram-разработчик + эксперт Rider–Waite–Smith + prompt engineer + UX-writer + дизайнер Telegram-графики (Pillow) + QA. Ты работаешь автономно, без уточняющих вопросов. Всё, что можно проверить кодом — проверяй кодом. Всё, что нельзя проверить — честно помечай как «требует ручной проверки».

## Рабочая директория

`C:/Users/IMYAREK/Voprosy/moira`

Используй `./.venv/Scripts/python.exe` для всех Python-команд.

## Контекст: что уже сделано (НЕ переделывай)

Следующие задачи **завершены предыдущими агентами** и подтверждены тестами (17 passed). Не переписывай и не откатывай:

- ✅ 78 карт, полный RU/EN, upright/reversed — `test_cards_78.py` зелёный
- ✅ Fallback composer — `test_fallback.py` зелёный
- ✅ «Мой Аркан»: 22/22 аркана, scoring без `% 22` — `test_patch5_i18n_quiz.py` зелёный
- ✅ i18n паритет: `ru.json` ↔ `en.json`, 0 расхождений
- ✅ 5-уровневый промпт, Pydantic-схема (headline, opening, card_interpretations, synthesis, practical_focus, reflection_question, voice_summary, share_summary)
- ✅ Контент-патчи 1–5 (карты, расклады, промпт, fallback, quiz) — в `docs/CONTENT_IMPROVEMENT_REPORT.md`
- ✅ Стабилизация — `docs/STABILIZATION_REPORT.md` (не откатывай)
- ✅ `docs/CONTENT_AUDIT.md`, `docs/CONTENT_SPEC.md`, `docs/READING_QUALITY_RUBRIC.md`

## Жёсткие запреты

1. **Не переписывай проект** — не меняй aiogram, БД-схему, тарифы, payment/referral, deployment
2. **Не откатывай** стабилизационные исправления (`docs/STABILIZATION_REPORT.md`)
3. **Не коммить, не пуши** — только изменения на диске
4. **RU и EN** — единственные языки, не добавляй другие
5. **Не пиши файлы вне** `C:/Users/IMYAREK/Voprosy/moira`
6. **Не используй** `ImageFont.load_default()` как основной шрифт — только аварийный fallback
7. **Не говори «сделано»** без доказательства (команда + вывод). Если файл не создан — задача не выполнена, скрипт упал — почини и перезапусти

## Что НЕ сделано (твои задачи)

Шесть блоков. Иди строго по порядку. После каждого — запускай тесты.

---

### Блок 1. Визуальная система и галерея (главный провал)

**Проблема:** в `artifacts/visual_review/` всего 4 файла. Нужно минимум 16.

#### 1.1. Design tokens

В `bot/visual/` создай модуль `tokens.py` с едиными токенами:
- цвета: фон, основной текст, вторичный текст, акцент, золото, рамка
- шрифты: основной + fallback
- отступы, радиусы, размеры заголовков/подписей
- размеры canvas: spread (1080×1080 или обосновать иное), share (1080×1350), altar, single card, quiz result

Запрет: магические числа в функциях Pillow. Все размеры/цвета/шрифты — из `tokens.py`.

Если в `bot/visual/render.py` уже есть hardcoded значения — замени на импорт из `tokens.py`.

#### 1.2. Шрифт

Проверь, есть ли в проекте project-local шрифт с поддержкой кириллицы + латиницы. Если нет — найди свободный (SIL Open Font License или MIT), скачай, положи в `assets/fonts/`, используй как основной. `ImageFont.load_default()` — только try/except fallback.

Проверь лицензию шрифта — запиши в `docs/VISUAL_REVIEW.md`.

#### 1.3. Галерея изображений

Сгенерируй в `artifacts/visual_review/` минимум 16 файлов:

| # | Файл | Сценарий |
|---|------|----------|
| 1 | `spread_situation_ru_upright.png` | «Ситуация» RU, все upright |
| 2 | `spread_situation_en_mixed.png` | «Ситуация» EN, mixed |
| 3 | `spread_love_ru_mixed.png` | «Любовь» RU, mixed |
| 4 | `spread_love_en_reversed.png` | «Любовь» EN, все reversed |
| 5 | `spread_choice_ru_mixed.png` | «Выбор» RU, mixed |
| 6 | `spread_choice_en_upright.png` | «Выбор» EN, все upright |
| 7 | `share_ru.png` | Share-карточка RU |
| 8 | `share_en.png` | Share-карточка EN |
| 9 | `altar_ru.png` | Алтарь RU |
| 10 | `altar_en.png` | Алтарь EN |
| 11 | `quiz_result_ru.png` | Результат «Мой Аркан» RU |
| 12 | `quiz_result_en.png` | Результат «Мой Аркан» EN |
| 13 | `long_ru_names.png` | Максимально длинные русские названия карт |
| 14 | `long_en_names.png` | Максимально длинные английские названия карт |
| 15 | `no_font_fallback.png` | Тест без основного шрифта (graceful degradation) |
| 16 | `missing_asset.png` | Тест без одного card asset (показать fallback) |

**Важно:** изучи сигнатуры функций в `bot/visual/render.py` ДО написания кода. Если функция `make_share_image` принимает `cards_info` как list of dict с ключами `{'label', 'card', 'reversed', 'name}` — передавай именно такие объекты, не путай `name` (строка) с `card` (TarotCard).

Каждое изображение проверь программно через Pillow:
```python
from PIL import Image
img = Image.open(path)
print(f'{path}: {img.size}, {img.mode}, {os.path.getsize(path)} bytes')
# Проверь: размер > 0, mode в (RGB, RGBA), размеры в разумных пределах
```

#### 1.4. Отчёт

Создай `docs/VISUAL_REVIEW.md`:
- Для каждого изображения: путь, размер в px, размер в KB, сценарий, результат (✅/❌), ограничения
- Запись о шрифте: название, лицензия, путь
- Запись о design tokens: где находится, какие токены

---

### Блок 2. Контентные тест-кейсы (48 сценариев)

**Проблема:** `tests/content_cases.json` и `tests/test_content_cases.py` не существуют.

#### 2.1. Сценарии

Создай `tests/content_cases.json` — 48 сценариев (8 × 3 расклада × RU/EN):

Покрой в каждом наборе из 8:
- все upright
- все reversed
- mixed (2 upright + 1 reversed)
- несколько Старших Арканов
- повтор одной масти
- конфликтующие карты (например, Император + Башня)
- эмоциональный вопрос («Любит ли он меня?»)
- нейтральный бытовой вопрос («Стоит ли менять работу?»)

Формат каждого сценария:
```json
{
  "id": "situation_ru_01",
  "spread": "situation",
  "lang": "ru",
  "question": "Что происходит в моей ситуации на работе?",
  "cards": [
    {"id": "major_00", "reversed": false},
    {"id": "minor_w_05", "reversed": true},
    {"id": "major_16", "reversed": false}
  ],
  "expect": {
    "must_reference_positions": true,
    "must_distinguish_reversal": true,
    "must_include_synthesis": true,
    "must_not_assert_other_person_thoughts": true,
    "must_include_reflection_question": true,
    "maximum_length": 3000
  }
}
```

#### 2.2. Тест-раннер

Создай `tests/test_content_cases.py`:
- Грузит `content_cases.json`
- Для каждого сценария вызывает `compose_fallback_reading()` (без LLM)
- Проверяет ожидаемые свойства:
  - `must_reference_positions`: текст содержит ссылки на позиции (суть/скрытый фактор/следующий шаг и т.д.)
  - `must_distinguish_reversal`: reversed-карта трактуется иначе чем upright
  - `must_include_synthesis`: есть блок синтеза/общего вывода
  - `must_not_assert_other_person_thoughts`: нет утверждений «он думает…», «она чувствует…»
  - `must_include_reflection_question`: есть вопрос для размышления
  - `maximum_length`: общая длина не превышает лимит

Запусти:
```
./.venv/Scripts/python.exe -m pytest tests/test_content_cases.py -v
```

Все 48 должны пройти. Если падают — исправь fallback composer, не тесты.

---

### Блок 3. Интеграционный smoke-тест

**Проблема:** бот никогда не запускался end-to-end, только импорты.

#### 3.1. Проверка импортов

```python
./.venv/Scripts/python.exe -c "
from bot.main import *  # или конкретные импорты, если * не работает
print('All imports OK')
"
```

Если падает — почини и повтори.

#### 3.2. End-to-end функции БЕЗ сети/LLM

Прогони и зафиксируй результат каждой:

1. `build_deck()` → вытяни 3 карты → `compose_fallback_reading()` на «Ситуации» RU и EN — текст валидный
2. `make_spread_image()` для расклада — изображение создалось, размеры в норме
3. `make_share_image()` — изображение создалось
4. `make_single_image()` для одной карты (upright + reversed) — изображение создалось
5. `quiz.compute_result()` на 5 разных наборах ответов — возвращает валидный аркан (0–21)
6. `voice_summary` — проверь, что в Pydantic-схеме это отдельное поле, не копия основного текста

Для каждого: ✅/❌ + точный вывод команды. Если падает — почини в рантайме.

#### 3.3. Голосовая ветка

Проверь `bot/voice/speaker.py`:
- `voice_summary` попадает в голосовой текст, а не обычный
- Запусти dry-run (mock TTS, без реального edge-tts вызова)
- Если логика сломана — почини

#### 3.4. Отчёт

Создай `docs/INTEGRATION_SMOKE.md`:
- Какие функции прогнал, статус каждой (✅/❌)
- Точный вывод ошибок, если были
- Команды для воспроизведения

---

### Блок 4. Аудит качества контента (выборочный)

Открой 5 случайных карт из `data_major.py` и 5 из `data_minor.py`.

Для каждой проверь:
- RU читается естественно, не калька с EN
- EN — neutral international English, не дословный перевод
- upright и reversed отличаются смыслом, а не одним словом
- Нет канцелярита («осуществление», «деятельность», повторы слов)
- Нет универсальных фраз («Вас ждут перемены», «Прислушайтесь к себе»)

Если найдёшь слабые места — исправь прямо в данных карт.

Зафиксируй проверенные карты и вердикт в `docs/FINAL_REPORT.md`.

---

### Блок 5. LLM-схема — проверка длин

Проверь Pydantic-схему в `bot/llm/adapter.py`:

| Поле | Ориентир |
|------|----------|
| headline | ≤ 90 символов |
| opening | 120–250 |
| card_interpretation (одна карта) | 300–550 |
| synthesis | 500–900 |
| practical_focus | 180–350 |
| reflection_question | ≤ 220 |
| voice_summary | 500–800 |
| share_summary | 180–300 |

Если в схеме нет валидаторов длины — добавь `Field(max_length=...)` или кастомный валидатор.

Проверь: `voice_summary` — отдельный устный текст, не копия `synthesis`. `share_summary` не содержит приватный вопрос пользователя.

---

### Блок 6. Финальные отчёты

Создай/обнови три файла:

#### 6.1. `docs/REVERIFICATION_REPORT.md`

```
# Отчёт перепроверки Moira

## Результаты тестов
[paste вывод pytest]

## Колода
[вывод проверки 78 карт]

## Fallback
[вывод проверки fallback]

## Мой Аркан
[вывод проверки 22 арканов]

## Визуал
[сводка из VISUAL_REVIEW.md]

## 48 контентных сценариев
[вывод test_content_cases.py]

## Интеграционный smoke
[сводка из INTEGRATION_SMOKE.md]

## Расхождения с предыдущим отчётом
[что было заявлено как «готово», но не было готово на самом деле]

## Что требует ручной проверки
- поллинг с реальным Telegram-токеном
- реальный TTS-звук (edge-tts)
- отрисовка на телефоне
- восприятие RU/EN пользователями
```

#### 6.2. `docs/FINAL_REPORT.md`

```
# Финальный отчёт Moira

## Сводка
Что было → что сделано в этой фазе

## Результаты тестов
Точные числа: N passed, M failed

## Интеграционный smoke
Статус по каждому пункту

## Аудит контента
Какие карты проверены, что исправлено

## Список созданных/изменённых файлов

## Что осталось на ручную проверку
Честно, без «всё готово»

## Готов ли бот к выкатке?
Да / Нет / С оговорками — с обоснованием
```

#### 6.3. Обнови `README.md`
Добавь секцию «Визуальная система» с описанием design tokens и шрифта.

---

## Порядок выполнения

1. **Блок 1** (визуал) → запуск `pytest tests/ -q`
2. **Блок 2** (48 сценариев) → запуск `pytest tests/test_content_cases.py -v`
3. **Блок 3** (smoke) → фиксация в `INTEGRATION_SMOKE.md`
4. **Блок 4** (аудит контента) → правки в данных карт
5. **Блок 5** (LLM-схема) → правки в adapter.py
6. **Блок 6** (отчёты) → финальные документы
7. Финальный прогон: `./.venv/Scripts/python.exe -m pytest tests/ -q` — все тесты зелёные

## Критерий завершения

Работа закончена, когда:
- `artifacts/visual_review/` содержит ≥16 проверенных изображений
- `docs/VISUAL_REVIEW.md` существует и описывает каждое изображение
- `tests/content_cases.json` содержит 48 сценариев
- `tests/test_content_cases.py` проходит (48/48)
- `docs/INTEGRATION_SMOKE.md` существует, все функции из Блока 3 отмечены ✅
- `docs/REVERIFICATION_REPORT.md` существует
- `docs/FINAL_REPORT.md` существует и отвечает «можно ли выкатывать?»
- Все тесты зелёные: `./.venv/Scripts/python.exe -m pytest tests/ -q`
- Ты честно перечислила, что НЕ проверила (поллинг, реальный TTS, телефон)

**Не пиши «визуал готов», пока в `artifacts/visual_review/` нет 16 файлов и они не проверены Pillow.**
**Не пиши «48 сценариев проходят», пока `test_content_cases.py` не запущен.**
**Не пиши «бот работает», пока функции из Блока 3 реально не отработали.**
