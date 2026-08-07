# План стабилизации Moira

## Исходное состояние

- **Git**: репозиторий не инициализирован (`git status` невозможен). Текущий код — рабочее дерево `C:/Users/IMYAREK/Voprosy/moira`.
- **Python**: 3.11 (по пути `.venv/Scripts/python.exe`).
- **Зависимости** (фактические из `.venv`):
  - aiogram 3.x, SQLAlchemy 2.0.x, aiosqlite 0.20+, alembic 1.18.x, instructor 1.15.x, openai 1.x, posthog 7.x, sentry-sdk 2.66.x, edge-tts 7.2.x, Pillow 12.3.x, pydantic 2.x.
- **Baseline**:
  - `compileall bot` — OK.
  - `alembic current` — `0002_growth (head)` после `stamp head` (таблицы фактически уже соответствовали head, `alembic_version` был пуст).
  - `alembic check` — `No new upgrade operations detected`.
  - `tests/smoke_test.py` — `ALL SMOKE TESTS PASSED`.
- **LLM provider** (по `.env` / `config.py`): OpenAI-compatible endpoint, умолчание `https://openrouter.ai/api/v1`, модель `deepseek/deepseek-chat`. В `bot.log` фактически виден `https://api.aigate.shop/v1/chat/completions` — значит в `.env` задан `LLM_BASE_URL=https://api.aigate.shop/v1`.

## Подтверждённые баги

| ID | Приоритет | Место | Проявление | Исправление | Тест |
|----|-----------|-------|------------|-------------|------|
| B1 | P0 | `bot/handlers/features.py:279` | `await FeatureStates.waiting_birth.set()` → `AttributeError: 'State' object has no attribute 'set'` (подтверждено логом и grep). | Заменить на `await state.set_state(FeatureStates.waiting_birth)`. | FSM-переход ввода даты рождения, повторный ввод, отмена. |
| B2 | P1 | `bot/handlers/reading.py:209-224` | `_consume_reading` использует read-modify-write в ORM без условного `UPDATE`/`rowcount`. | Сделать атомарный conditional UPDATE с `rowcount` и идемпотентным логом. | Параллельное списание одного кредита. |
| B3 | P1 | `bot/handlers/payment.py:103-135` | Проверка `existing` идёт через `SELECT`, затем `INSERT`; между ними race condition. | Перейти на `INSERT ... ON CONFLICT` / обработку `IntegrityError` в одной транзакции. | Параллельный successful payment. |
| B4 | P1 | `bot/llm/adapter.py:137-173` | Внешний цикл `for attempt in range(2)` + `max_retries=2` в Instructor → вложенные retries. | Убрать вложенность: `max_retries=0` в Instructor, один форматный retry в коде, затем fallback. | LLM timeout/truncation, fallback. |
| B5 | P1 | `bot/handlers/reading.py:101-130` | Списание происходит до генерации и сохранения расклада; технический сбой забирает кредит без компенсации. | Модель `pending → completed/failed` с компенсацией; списание либо отложить, либо компенсировать при ошибке. | Технический сбой не забирает право. |
| B6 | P2 | `bot/keyboards.py:51-59` | `paywall_kb()` захардкожена на английском, игнорирует locale. | Использовать `t(lang, ...)` для всех кнопок paywall. | Паритет RU/EN. |
| B7 | P2 | `bot/visual/render.py:11` | Путь к шрифтам `C:/Windows/Fonts` — Windows-only. | Добавить project-local fallback + проверку существования. | Отсутствующий font. |
| B8 | P2 | `bot/services/analytics.py:57-61` | В PostHog уходят все props без allowlist. | Разрешить только allowlist свойств; чувствительные данные отфильтровывать. | Privacy PostHog. |
| B9 | P2 | `bot/main.py:52-72` | `before_send` не скрапит exception messages / prompts / user content. | Добавить scrubbing exception values и корреляционный ID. | Privacy Sentry. |
| B10 | P2 | `bot/handlers/features.py:410-427` | `_toggle_favorite` при `IntegrityError` возвращает `True`, не синхронизируя UI с БД. | После rollback повторно проверить наличие строки и вернуть фактическое состояние. | Параллельное добавление favorite. |
| B11 | P2 | `bot/handlers/admin.py:30` | `select(func.count().select_from(Payment), func.sum(Payment.stars))` — подозрительная конструкция; может строить неправильный SQL. | Исправить на корректный запрос count + sum. | /stats работает. |

## Высоковероятные риски

| ID | Приоритет | Место | Риск | Статус |
|----|-----------|-------|------|--------|
| R1 | P1 | `bot/handlers/reading.py:131-138` | `answer_voice()` упадёт с `VOICE_MESSAGES_FORBIDDEN` для пользователей, отключивших voice. Сейчас обёрнуто, но голос отправляется автоматически. | Будет обработано: сначала текст+картинка, TTS — отдельная кнопка/опция. |
| R2 | P1 | `bot/handlers/payment.py:155-180` | Refund отзывает права unconditionally (`free_readings = max(0, free_readings - amount)`), даже если пакет частично использован. | Зафиксировать безопасное правило в коде/документации. |
| R3 | P1 | `bot/llm/adapter.py` | Персональные данные (история interpretations) передаются в LLM. | Ограничить memory и не передавать Telegram ID/username. |
| R4 | P2 | `bot/handlers/features.py:366-393` | Daily push помечает `last_push_date` при `daily_push=False`, что влияет на поведение после включения. | Проверить/исправить логику. |
| R5 | P2 | `bot/handlers/reading.py:140-166` | Reading сохраняется после отправки голоса; если TTS/голос упадёт, reading всё равно сохранится. | Сохранить reading после успешного текстового результата, независимо от голоса. |
| R6 | P2 | — | Отсутствует команда/flow удаления пользовательских данных. | Добавить `/delete_my_data` и соответствующие i18n-ключи. |
| R7 | P2 | `bot/handlers/features.py:47-147` | Тест «Мой Аркан» использует 6 вопросов (согласно README), но JSON-черновик предлагает 7 и `% 22` scoring. | Синхронизировать README, код, RU/EN; оставить 6 вопросов с явной scoring matrix. |

## Статус выполнения

| Патч | Статус | Тесты |
|------|--------|-------|
| Patch 1 — runtime blockers | ✅ | `tests/test_patch1_runtime.py` |
| Patch 2 — финансовая корректность | ✅ | `tests/test_patch2_payments.py` |
| Patch 3 — LLM, prompts, fallback | ✅ | `tests/test_patch3_llm.py` |
| Patch 4 — критические тесты | ✅ | `tests/test_patch4_critical.py` |
| Patch 5 — RU/EN, onboarding, «Мой Аркан» | ✅ | `tests/test_patch5_i18n_quiz.py` |
| Patch 6 — фоновые задачи, история, share, favorites | ✅ | `tests/test_patch6_background.py` |
| Patch 7 — observability, assets, README | ✅ | README обновлён; Sentry/PostHog scrubbing добавлен |

## Последовательность патчей (выполнено)

### Patch 1 — runtime blockers
- ✅ Исправлен `FeatureStates.waiting_birth.set()` → `state.set_state(...)`.
- ✅ Добавлена обработка `TelegramBadRequest` для голоса: voice → audio → notice.
- ✅ Исправлен `paywall_kb` на i18n.
- ✅ Исправлен админ `/stats` SQL.

### Patch 2 — финансовая корректность
- ✅ `_consume_reading` переписан на атомарный conditional UPDATE (promo → free → unlimited).
- ✅ `on_payment` переведён на идемпотентный INSERT с `IntegrityError`.
- ✅ Уточнён refund: no-op при повторе, безопасное отзывание прав.
- ✅ Добавлена компенсация кредита при сбое генерации расклада.

### Patch 3 — LLM, prompts, fallback
- ✅ Убраны вложенные retries (`max_retries=0` Instructor + один retry в коде).
- ✅ Добавлена `CardInterpretation` с `position`/`text` и лимитами.
- ✅ Добавлен `voice_summary` и лимиты на все поля.
- ✅ Добавлен safety pre-filter для чувствительных тем и prompt injection.
- ✅ Memory ограничена; Telegram ID/username не передаются.

### Patch 4 — критические тесты
- ✅ Добавлены standalone regression tests для concurrency, Alembic, assets, fonts, data deletion, privacy.

### Patch 5 — RU/EN, onboarding, «Мой Аркан», i18n
- ✅ Ключи RU/EN синхронизированы; добавлены safety/data deletion/voice keys.
- ✅ «Мой Аркан»: 6 вопросов, tie-break к младшему аркану.

### Patch 6 — фоновые задачи, история, share, favorites
- ✅ Daily push обновляет `last_push_date` только после успешной отправки.
- ✅ Weekly mirror защищён от дублей через `last_mirror_week`.
- ✅ `_toggle_favorite` идемпотентен при параллельных вызовах.

### Patch 7 — observability, assets, README
- ✅ Sentry `before_send` redact exception values / request data / user PII.
- ✅ PostHog allowlist свойств.
- ✅ Fallback для шрифтов (project-local + OS + load_default).
- ✅ README разделён и синхронизирован с кодом.

## Файлы, которые предполагается изменить

- `bot/handlers/features.py`
- `bot/handlers/reading.py`
- `bot/handlers/payment.py`
- `bot/handlers/admin.py`
- `bot/handlers/start.py` (data deletion)
- `bot/llm/adapter.py`
- `bot/keyboards.py`
- `bot/visual/render.py`
- `bot/services/analytics.py`
- `bot/main.py`
- `bot/db/models.py` (возможно дополнительные поля llm_usage)
- `bot/i18n/locales/ru.json`
- `bot/i18n/locales/en.json`
- `tests/smoke_test.py`
- `tests/test_*.py` (новые)
- `README.md`
- `docs/STABILIZATION_REPORT.md`
