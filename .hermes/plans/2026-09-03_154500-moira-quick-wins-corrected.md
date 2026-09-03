# Moira — Corrected Quick Wins Plan (2026-09-03)

> **For Hermes:** Use autonomous agent delegation (claude-code / codex / opencode) to implement task-by-task.  
> Each QW is independently deployable; preferred order below but not strictly dependent.

**Goal:** Implement the 6 Quick Wins (QW-0…QW-6) from the conversation analysis, corrected against actual codebase state as of commit 57c43a2.

**Architecture:** SQLite/PostgreSQL + aiogram 3 + OpenRouter (free-tier models) + SQLAlchemy 2.0 async.  
**Tech Stack:** Python 3.11, uv, pytest, alembic, pydantic v2.

---

## Corrected Baseline (verified against code)

| Item | Original Claim | **Actual State** |
|------|----------------|------------------|
| Tests | "175 tests" | **177 collected** (121 sync + 56 async coroutines) |
| `Reading` model | missing `generation_id`, `result_json` | **Confirmed missing** — 9 columns only |
| `LlmUsage` | has `request_id` (uuid4 hex) | **Yes**, but no `generation_id` column |
| `_new_request_id()` | exists in adapter | **Yes** at `bot/llm/adapter.py:114` |
| Minor Arcana symbols | "22 of 78 have symbols" | **0/56** minor cards have symbols — only Major (22) |
| Position-aware fields | "4 of 10 filled" | **0/78** for all 6 extended fields (blocked_expression, excess_or_deficit, relationship, career, inner_state, decision) |
| `daily_push_loop` | legacy, V2 table exists | **Confirmed**: `daily_push_loop` at `main.py:112`, `PushDelivery` table created (migration 0008) but **not used** in main |
| PushDelivery service | imported? | **Not imported** in `main.py` — V2 scheduler not wired |
| Quality harness | exists | **Yes**: `READING_QUALITY_RUBRIC.md`, `test_cards_78.py`, `test_quality_eval_fixture.py` |

---

## QW-0. Provenance + Feedback Foundation (Блокирует измеримость всего остального)

**Файлы:** `bot/db/models.py`, `bot/llm/adapter.py` (`_log_usage`, `interpret_reading`), `bot/handlers/reading.py` (`cb_feedback`), миграция `0009_reading_provenance_feedback.py`

**Задачи:**

### Task 0.1: Add columns to `Reading` model
- **Modify:** `bot/db/models.py:47-59` (Reading class)
- Add: `generation_id` (String(64), nullable, indexed), `result_json` (Text, nullable), `draw_engine_version`, `deck_version`, `spread_version`, `prompt_version` (all String(32), nullable)
- **Test:** `tests/test_models.py::test_reading_has_provenance_fields`

### Task 0.2: Add `generation_id` to `LlmUsage`
- **Modify:** `bot/db/models.py:148-171` (LlmUsage class)
- Add: `generation_id` (String(64), nullable, indexed) — **не путать с `request_id`**
- **Test:** `tests/test_models.py::test_llm_usage_has_generation_id`

### Task 0.3: Create `ReadingFeedback` table + migration
- **Create:** `alembic/versions/0009_reading_provenance_feedback.py`
- Table: `id, user_id, reading_id, generation_id(nullable), value(Enum: positive|negative), checkpoint(Enum: immediate), created_at` + unique `(user_id, reading_id, checkpoint)`
- **Test:** `tests/test_models.py::test_reading_feedback_table`

### Task 0.4: Wire `generation_id` through LLM call
- **Modify:** `bot/llm/adapter.py` — в `interpret_reading` вызвать `_new_request_id()` **один раз** в начале, передать как `generation_id` в `_log_usage` и вернуть в результате
- В `Reading` сохранять `generation_id` и валидированный `result_json` (Pydantic-модель, не raw provider output)
- **Test:** `tests/test_llm_integration.py::test_generation_id_propagates`

### Task 0.5: Persist feedback in `cb_feedback`
- **Modify:** `bot/handlers/reading.py:405-444` — писать в `ReadingFeedback` вместо/вместе с analytics event
- **Test:** `tests/test_handlers.py::test_feedback_creates_reading_feedback_row`

### Task 0.6: Verification query
```sql
-- % positive feedback по модели/промпту/раскладу/языку
SELECT 
  lu.model, lu.prompt_version, r.spread, u.language,
  COUNT(*) as total,
  SUM(CASE WHEN rf.value = 'positive' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as pct_positive
FROM reading_feedback rf
JOIN readings r ON rf.reading_id = r.id
JOIN llm_usage lu ON rf.generation_id = lu.generation_id
JOIN users u ON r.user_id = u.id
GROUP BY lu.model, lu.prompt_version, r.spread, u.language;
```

---

## QW-1. `secrets.SystemRandom` + Provenance Fields (15 мин)

**Файл:** `bot/tarot/spreads.py:108,117`, `bot/db/models.py` (Reading — поля из QW-0)

### Task 1.1: Replace `random` with `secrets.SystemRandom`
- **Modify:** `bot/tarot/spreads.py`
```python
# Line ~1: add import
import secrets
_rng = secrets.SystemRandom()  # module level

# Line 108: _rng.shuffle(deck)
# Line 117: reversed = _rng.random() < REVERSED_CHANCE
```
- **Не трогать** `bot/astro/calc.py:176` (daily card — отдельный `Random(day + "#" + user_id)`)

### Task 1.2: Fill provenance fields on Reading creation
- **Modify:** `bot/handlers/reading.py` в `run_reading` где создаётся `Reading`
- Заполнить: `draw_engine_version="1.0"`, `deck_version="rws-78"`, `spread_version=spread_id`, `prompt_version=PROMPT_VERSION` (из adapter)
- **Test:** `tests/test_spreads.py::test_draw_uses_system_random`

---

## QW-2. Symbols для 56 младших карт (Контент, 0 кода)

**Файлы:** `bot/tarot/data_symbols.py` (добавить `MINOR_SYMBOLS`), `bot/tarot/deck.py:_build_minor`

### Task 2.1: Add `MINOR_SYMBOLS` dict
- **Modify:** `bot/tarot/data_symbols.py` — добавить после `MAJOR_SYMBOLS`
- Структура: `{suit: {rank: {"ru": [...], "en": [...]}}}` для 4 мастей × 14 рангов (Ace-10, Page, Knight, Queen, King) = 56 записей
- 2–3 символа на карту (RWS tradition)

### Task 2.2: Wire symbols into minor card construction
- **Modify:** `bot/tarot/deck.py:_build_minor` (lines 166-185)
- Передать `symbols=MINOR_SYMBOLS.get(suit_id, {}).get(rank_id, {}).get(lang, [])` в `LocalizedCard`
- **Test:** `tests/test_cards_78.py::test_minor_have_symbols` (новый тест)

### Task 2.3: Quality harness before/after
- Запустить `test_cards_78.py` + quality rubric **до** и **после** добавления символов
- Метрика: доля раскладов с ≥1 символом в minor карте в prompt

---

## QW-3. Deterministic Card Pattern Analyzer (A/B через PROMPT_VERSION)

**Новый файл:** `bot/tarot/patterns.py`  
**Точка внедрения:** `bot/llm/adapter.py:_build_user_message` (line 525) и/или `_build_card_block` (line 446)

### Task 3.1: Create `patterns.py`
- **Create:** `bot/tarot/patterns.py`
- Функция `analyze_pattern(drawn: list[DrawnCard]) -> str` возвращает компактный блок (5–7 строк):
  - `major_count/minor_count`
  - `dominant_suit` (только при явном перевесе, не при ничьей)
  - `reversed_count`
  - `keyword_overlaps` (пересечения keywords между картами)
  - `position_sequence` (порядок позиций в раскладе)
- **Никаких LLM вызовов** — чистая детерминированная логика

### Task 3.2: A/B integration via `PROMPT_VERSION`
- **Modify:** `bot/llm/adapter.py` — добавить `PROMPT_VERSION_V2 = "v6-pattern-analyzer"` (или инкремент)
- В `_build_user_message`: если `cfg.prompt_version == "v6-pattern-analyzer"` — инжектировать `analyze_pattern(drawn)` перед format rules
- **Критично:** блок с оговоркой *"используй только как поддерживающий контекст, не выдумывай дополнительные паттерны"*

### Task 3.3: Quality gate before merge
- Прогон `test_quality_eval_fixture.py` + рубрика `READING_QUALITY_RUBRIC.md` на обеих версиях промпта
- Метрики: quality score + positive feedback rate (нужен QW-0)
- **Test:** `tests/test_patterns.py::test_analyze_pattern_output`

---

## QW-4. Заметка к раскладу (Retention за полдня)

**Файлы:** `bot/db/models.py`, миграция `0010_reading_note.py`, handlers, keyboards

### Task 4.1: Add `ReadingNote` model + migration
- **Modify:** `bot/db/models.py` — добавить класс `ReadingNote`
- **Create:** `alembic/versions/0010_reading_note.py`
- Поля: `id, user_id, reading_id, text, created_at, updated_at` + unique `reading_id`
- Max length: 500–1000 chars

### Task 4.2: CRUD handlers + keyboards
- **Modify:** `bot/handlers/reading.py` — добавить колбэки `note:save`, `note:edit`, `note:delete`
- **Modify:** `bot/keyboards.py` — кнопка "📝 Заметка" после расклада и в истории
- Ownership check: `note.user_id == callback.from_user.id`
- Каскад в `/delete_my_data`

### Task 4.3: Privacy guards
- **Не** логировать текст заметки в analytics/Sentry
- **Не** подмешивать в будущие LLM-prompts (в этом спринте)

---

## QW-5. «Просто спросить Мойру» — Onboarding Classifier (0 LLM)

**Новый файл:** `bot/tarot/recommender.py`  
**Интеграция:** `bot/handlers/start.py` или `reading.py` (точка входа после `/start`)

### Task 5.1: Create deterministic classifier
- **Create:** `bot/tarot/recommender.py`
```python
def recommend_spread(question: str, lang: str) -> str:
    q = question.lower()
    love_kw = {"любовь","отношения","партнёр","расставание","чувства","love","relationship","partner","breakup","feelings"}
    choice_kw = {"выбор","что выбрать","а или б","стоит ли","compare","option","two paths","decide"}
    if any(k in q for k in love_kw): return "love"
    if any(k in q for k in choice_kw): return "choice"
    return "situation"
```

### Task 5.2: UI flow
- Пользователь пишет вопрос → бот показывает рекомендованный расклад + кнопку «Подтвердить» / «Другой»
- Платный reading **не запускается** до подтверждения
- Events: `smart_spread_started`, `recommended`, `accepted`, `changed` — **без текста вопроса**

---

## QW-6. «Мои карты» 7/30 дней (Накопительная ценность, 0 LLM)

**Новый файл:** `bot/services/reading_insights.py`  
**Переиспользовать:** `_top_cards_of_week` (`bot/handlers/features.py:473`), `weekly_mirror_text`

### Task 6.1: Create insights service
- **Create:** `bot/services/reading_insights.py`
- Функция `get_user_insights(user_id: int, days: int) -> dict`:
  - Число раскладов, Major %, масти, dominant suit, top-3 карты, реверсы, распределение spread, повторы ≥2
  - Источник: `Reading.cards_json`
  - При `<3` раскладов — честный текст «нужно хотя бы 3 расклада», **не** вызывать LLM

### Task 6.2: Handlers + keyboards
- **Modify:** `bot/handlers/features.py` — добавить `/my_cards` или кнопку в меню
- Периоды: 7 дней / 30 дней (callback `insights:7`, `insights:30`)
- **Не делать:** emotional score, destiny score, «точность предсказаний»

---

## Medium Wins (M1–M5) — Dependencies Map

| # | Task | Blocks | Depends On |
|---|------|--------|------------|
| **M1** | Persistent feedback + check-in d1/d7 | Нить Мойры (B1) | M2 |
| **M2** | **PushDelivery V2** — заменить `daily_push_loop` воркером на `PushDelivery` | Все reminder-фичи, B1, B2 | — |
| **M3** | Position-aware meanings (заполнение 6 полей для 22 Старших) | Рост качества трактовок | — (контент) |
| **M4** | AI follow-up / what-if (`interpret_followup`) | Монетизация глубины | QW-0 (`result_json`) |
| **M5** | Одна уточняющая карта (`parent_reading_id`) | Продление сессии | Платежная политика |

---

## Big Bets (B1–B5) — 1–3 недели

| # | Bet | Effect | Precondition |
|---|-----|--------|--------------|
| **B1** | **«Нити Мойры»** — явная пользовательская память | Key differentiator vs one-shot tarot bots | M1, M2 |
| **B2** | **«Утро с Мойрой»** — персонализированный brief | Retention leap; replaces content card with assistant | M2, B1 |
| **B3** | **«Три голоса Мойры»** (Символист/Зеркало/Скептик) — premium, по кнопке | Ощущение глубины + монетизация | QW-3, M4 |
| **B4** | Internal scoreboard (pos-feedback по модели/промпту/раскладу/языку) | Quality → manageable metric | QW-0 |
| **B5** | Astronomy Engine (`cosinekitty/astronomy`) — **сначала валидатор** `calc.py` в тестах | Достоверность астрослоя | — |

---

## Execution Order (Dependency Graph)

```
QW-0  provenance + feedback  ──┐
QW-1  SystemRandom (15 мин)    │
QW-2  символы минорных карт    ├─ quality-слой (QW-2 контент)
QW-3  Pattern Analyzer (A/B)   ─┘
           │
QW-4  заметка ─ QW-5 спросить ─ QW-6 мои карты   ← retention-слой
           │
M2  PushDelivery V2 ──► M1 check-in ──► B1 Нити ──► B2 Утро с Мойрой
           │
M3 position-aware (контент) ──► M4 what-if ──► B3 Три голоса
           │
B4 scoreboard (на QW-0)
B5 astronomy validator (тесты)
```

---

## Agent Delegation Strategy

| Task | Agent | Why |
|------|-------|-----|
| **QW-0, QW-1, QW-3, QW-4, QW-5, QW-6** | **Claude Code / Codex / OpenCode** (local repo access) | Multi-file edits, migrations, tests, integration |
| **QW-2 (symbols content)** | **ChatGPT SOL** (no local access) | Pure content generation — 56 cards × 2–3 symbols × RU/EN. Give it the schema and 5 Major examples; it returns JSON. |
| **M3 (position-aware content)** | **ChatGPT SOL** | 22 Major × 6 fields × RU/EN = 264 strings. Schema + examples in prompt. |
| **M2 (PushDelivery V2 worker)** | **Claude Code** | Requires scheduler refactor, idempotency, lease logic — code-heavy |
| **B5 (astronomy validator)** | **Codex** | Add test dependency, compare `calc.py` vs `astronomy` outputs |

---

## Delegation Prompts (Ready to Copy)

### For QW-2 (ChatGPT SOL — content only)
```
Generate visual symbols for 56 Minor Arcana cards (RWS tradition).
Input: suit (wands/cups/swords/pentacles), rank (ace..10, page, knight, queen, king).
Output: JSON { "wands": { "ace": {"ru":["...","..."], "en":["...","..."]}, ... } }
2-3 symbols per card. Style matches Major examples:
  Major 0 (Fool): ru=["белый цветок","обрыв","малый мешок"], en=["white flower","cliff edge","small bundle"]
  Major 1 (Magician): ru=["бесконечность над головой","четыре масти на столе","жезл"], en=["lemniscate above","four suits on the table","wand"]
Return ONLY valid JSON.
```

### For M3 (ChatGPT SOL — content only)
```
Fill 6 position-aware fields for 22 Major Arcana (RU + EN).
Fields: blocked_expression, excess_or_deficit, relationship, career, inner_state, decision.
Schema per field: 1-2 sentences, grounded in card meaning, not generic psychology.
Position mapping (example):
  love/you → inner_state
  love/dynamic → relationship
  situation/hidden → blocked_expression
  choice/criterion → decision
Reference: existing essence/light/shadow/advice in data_major.py.
Return JSON: { "0": { "ru": { "inner_state": "...", ... }, "en": {...} }, ... }
```

---

## Verification Checklist (per QW)

| QW | Verification |
|----|--------------|
| QW-0 | SQL query returns % positive by model/prompt/spread/lang |
| QW-1 | `test_spreads.py` passes; `draw_engine_version` saved in Reading |
| QW-2 | `test_cards_78.py::test_minor_have_symbols` passes; quality rubric delta ≥ 0 |
| QW-3 | A/B: `PROMPT_VERSION=v6-pattern-analyzer` measurable quality + feedback lift |
| QW-4 | Note CRUD works; ownership enforced; cascade delete verified |
| QW-5 | Classifier accuracy on 50 test questions ≥ 90%; confirmation flow works |
| QW-6 | Insights for user with ≥3 readings returns non-empty dict; <3 returns honest message |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| QW-0 migration on prod DB | Test migration on staging SQLite + PG; backup before apply |
| QW-3 pattern block degrades quality | A/B gate: only merge if quality_rubric score ≥ baseline AND positive_feedback ≥ baseline |
| QW-2 content quality | Peer review 10% sample; automate "no empty symbols" test |
| M2 PushDelivery race conditions | Lease + idempotency key (uq_push_delivery_user_kind_period) already in migration 0008 |
| B5 astronomy precision | Validate only; don't replace `calc.py` until test parity ≥ 99.9% |

---

## What NOT to Do (Confirmed)

- ❌ Brier score / hit rate / «точность таро» — противоречит концепции Moira
- ❌ Global Health Score 1–100 — псевдодиагностика
- ❌ 4-agent swarm / Council на каждый расклад — дорого, псевдоконсенсус
- ❌ RAG / vector DB — не нужно, есть детерминированный контекст + 78 карт
- ❌ MCP / FastAPI-агент — нет внешних потребителей
- ❌ 11 новых раскладов — масштабирует поддержку контента, не глубину
- ❌ Вторая scheduler-архитектура — сначала M2
- ❌ Починка `MemoryStore(":memory:")` — это не баг, а отсутствие фичи; чинится через B1 (Нити)

---

## Files to Create/Modify Summary

| File | Action |
|------|--------|
| `bot/db/models.py` | Add Reading fields, LlmUsage.generation_id, ReadingFeedback, ReadingNote |
| `alembic/versions/0009_reading_provenance_feedback.py` | Create |
| `alembic/versions/0010_reading_note.py` | Create |
| `bot/llm/adapter.py` | Wire generation_id, A/B prompt version, pattern injection |
| `bot/tarot/spreads.py` | SystemRandom + provenance fields |
| `bot/tarot/data_symbols.py` | Add MINOR_SYMBOLS |
| `bot/tarot/deck.py` | Wire minor symbols |
| `bot/tarot/patterns.py` | **Create** |
| `bot/tarot/recommender.py` | **Create** |
| `bot/services/reading_insights.py` | **Create** |
| `bot/handlers/reading.py` | Feedback → ReadingFeedback, Note CRUD |
| `bot/handlers/features.py` | Insights handlers |
| `bot/keyboards.py` | Note + recommender keyboards |
| `tests/test_cards_78.py` | Add `test_minor_have_symbols` |
| `tests/test_patterns.py` | **Create** |
| `tests/test_recommender.py` | **Create** |
| `tests/test_insights.py` | **Create** |