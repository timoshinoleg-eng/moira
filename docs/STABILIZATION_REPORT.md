# Отчёт по стабилизации Moira

## Исходное состояние

- **Commit**: N/A — рабочая директория не является Git-репозиторием (`git rev-parse --show-toplevel` возвращает `fatal: not a git repository`).
- **Ветка**: N/A.
- **Python**: 3.11.15 (`C:/Users/IMYAREK/Voprosy/moira/.venv/Scripts/python.exe`).
- **Зависимости** (фактические версии из `.venv`):
  - aiogram 3.30.0
  - SQLAlchemy 2.0.51
  - alembic 1.18.5
  - instructor 1.15.4
  - openai 2.53.0
  - posthog 7.37.0
  - sentry-sdk 2.66.1
  - edge-tts 7.2.8
  - Pillow 12.3.0
  - pydantic 2.13.4
- **LLM provider** (по `.env` / `bot/config.py`): OpenAI-compatible endpoint, умолчание `https://openrouter.ai/api/v1`, модель `deepseek/deepseek-chat`. В `bot.log` фактически виден `https://api.aigate.shop/v1/chat/completions` — в `.env` задан `LLM_BASE_URL=https://api.aigate.shop/v1`.
- **Baseline-результат** (проверено перед созданием отчёта):
  - `python -m compileall bot` — OK.
  - `python -m alembic current` — `0002_growth (head)`.
  - `python -m alembic check` — `No new upgrade operations detected`.
  - `python tests/smoke_test.py` — `ALL SMOKE TESTS PASSED`.
  - `python tests/test_patch1_runtime.py` — `PATCH 1 TESTS PASSED`.
  - `python tests/test_patch2_payments.py` — `PATCH 2 TESTS PASSED`.
  - `python tests/test_patch3_llm.py` — `PATCH 3 TESTS PASSED`.
  - `python tests/test_patch4_critical.py` — `PATCH 4 CRITICAL TESTS PASSED`.
  - `python tests/test_patch5_i18n_quiz.py` — `PATCH 5 TESTS PASSED`.
  - `python tests/test_patch6_background.py` — `PATCH 6 TESTS PASSED`.

## Подтверждённые баги

| ID | Приоритет | Место | Проявление | Исправление | Тест |
|----|-----------|-------|------------|-------------|------|
| B1 | P0 | `bot/handlers/features.py` | `await FeatureStates.waiting_birth.set()` → `AttributeError: 'State' object has no attribute 'set'` (подтверждено логом и grep). | Заменено на `await state.set_state(FeatureStates.waiting_birth)`; аналогично для `PromoStates.waiting_code`. | `tests/test_patch1_runtime.py` — переход ввода даты рождения, повторный ввод, отмена, очистка FSM. |
| B2 | P1 | `bot/handlers/reading.py` | `_consume_reading` использовал read-modify-write в ORM без условного `UPDATE`/`rowcount` — риск двойного списания. | Атомарный conditional UPDATE с проверкой `rowcount`, порядок: promo → free → unlimited (не списывается). | `tests/test_patch2_payments.py` — параллельное списание одного кредита. |
| B3 | P1 | `bot/handlers/payment.py` | Проверка `existing` через `SELECT`, затем `INSERT` — race condition при параллельном платеже. | Идемпотентный INSERT с обработкой `IntegrityError` на уникальном `telegram_payment_charge_id`. | `tests/test_patch2_payments.py` — повторный и параллельный successful payment. |
| B4 | P1 | `bot/llm/adapter.py` | Внешний цикл retry + `max_retries` в Instructor → вложенные retries и задержки при truncation. | `max_retries=0` в Instructor, один явный retry в коде, затем встроенный fallback. | `tests/test_patch3_llm.py` — timeout, truncation, fallback, неверное число interpretation. |
| B5 | P1 | `bot/handlers/reading.py` | Списание происходило до генерации расклада; технический сбой забирал кредит без компенсации. | Введена модель `pending → completed/failed`; при ошибке выполняется компенсация кредита. | `tests/test_patch2_payments.py` — технический сбой не забирает право. |
| B6 | P2 | `bot/keyboards.py` | `paywall_kb()` была захардкожена на английском. | Все кнопки paywall используют `t(lang, ...)`. | `tests/test_patch5_i18n_quiz.py` — паритет RU/EN. |
| B7 | P2 | `bot/visual/render.py` | Windows-only путь `C:/Windows/Fonts`. | Добавлен project-local fallback, OS-agnostic поиск, `load_default()` в крайнем случае. | `tests/test_patch4_critical.py` — отсутствующий font. |
| B8 | P2 | `bot/services/analytics.py` | PostHog получал все props без allowlist. | Разрешён только allowlist: locale, spread_type, payment_product, prompt_version, fallback_used, latency_bucket, is_returning_user. | `tests/test_patch4_critical.py` — privacy PostHog. |
| B9 | P2 | `bot/main.py` | `before_send` не скрапил exception values / prompts / user content. | Добавлен `_scrub_sensitive`: redact сообщений, prompt, Authorization, токенов, даты рождения, username; добавлен `correlation_id`. | `tests/test_patch4_critical.py` — privacy Sentry. |
| B10 | P2 | `bot/handlers/features.py` | `_toggle_favorite` при `IntegrityError` возвращал `True`, не синхронизируя UI с БД. | После rollback повторно проверяется наличие строки и возвращается фактическое состояние. | `tests/test_patch4_critical.py` — параллельное добавление favorite. |
| B11 | P2 | `bot/handlers/admin.py` | `select(func.count().select_from(Payment), func.sum(Payment.stars))` — подозрительная конструкция. | Исправлен на корректный запрос count + sum. | `tests/test_patch1_runtime.py` + ручная проверка `/stats`. |

## Высоковероятные риски

| ID | Приоритет | Место | Риск | Статус |
|----|-----------|-------|------|--------|
| R1 | P1 | `bot/handlers/reading.py` | `answer_voice()` падает с `VOICE_MESSAGES_FORBIDDEN` для пользователей, отключивших voice. | Обработан: сначала отправляется текст+картинка, TTS — отдельная кнопка/fallback; voice errors перехватываются и пробуется audio, затем текстовое уведомление. |
| R2 | P1 | `bot/handlers/payment.py` | Refund отзывал права unconditionally, даже если пакет частично использован. | Зафиксировано безопасное правило: отзываются только неиспользованные чтения/дни в рамках продукта; отрицательный баланс исключён. |
| R3 | P1 | `bot/llm/adapter.py` | Персональные данные (история interpretations) передавались в LLM. | Ограничена memory; Telegram ID/username не передаются; используется производный астрологический контекст вместо точной даты рождения. |
| R4 | P2 | `bot/handlers/features.py` | Daily push помечал `last_push_date` при `daily_push=False`. | Исправлено: `last_push_date` обновляется только после успешной отправки и только если push включён. |
| R5 | P2 | `bot/handlers/reading.py` | Reading сохранялся после отправки голоса; TTS-ошибка влияла на статус. | Reading сохраняется после успешного текстового результата; голос/TTS не меняет статус. |
| R6 | P2 | `bot/handlers/start.py` | Отсутствовал flow удаления пользовательских данных. | Добавлена команда `/delete_my_data` и соответствующие i18n-ключи. |
| R7 | P2 | `bot/handlers/features.py` | Тест «Мой Аркан»: расхождение по числу вопросов и `% 22` scoring. | Синхронизировано: 6 вопросов, явная scoring matrix, tie-break к младшему аркану; README, RU, EN и тесты приведены в соответствие. |

## Выполненные изменения

### Patch 1 — runtime blockers
- Исправлен устаревший FSM API: `FeatureStates.waiting_birth.set()` → `await state.set_state(FeatureStates.waiting_birth)`.
- Исправлен `PromoStates.waiting_code.set()` → `await state.set_state(PromoStates.waiting_code)`.
- Добавлена обработка `TelegramBadRequest` для голоса: voice → audio fallback → локализованное уведомление.
- Исправлен `paywall_kb()` на i18n (`t(lang, ...)`).
- Исправлен админ `/stats` SQL.

### Patch 2 — финансовая корректность
- `_consume_reading` переписан на атомарный conditional UPDATE с проверкой `rowcount`.
- Зафиксирован порядок списания: promo → free → unlimited (не списывается).
- `on_payment` переведён на идемпотентный INSERT с обработкой `IntegrityError` по `telegram_payment_charge_id`.
- Уточнён refund: no-op при повторе, безопасное отзывание прав, аудит.
- Добавлена компенсация кредита при сбое генерации расклада.

### Patch 3 — LLM, prompts, fallback
- Убраны вложенные retries: `max_retries=0` в Instructor, один явный retry в коде.
- Введена структурированная схема `CardInterpretation` + `TarotReadingResult` с Pydantic-лимитами.
- Добавлены `voice_summary`, `share_summary`, `reflection_question` с разумными ограничениями длины.
- Добавлен safety pre-filter для медицинских, юридических, финансовых, кризисных запросов и prompt injection.
- Memory ограничена; Telegram ID/username не передаются в LLM.
- Добавлено логирование `llm_usage`: provider, model, prompt_version, schema_version, input_tokens, output_tokens, latency_ms, attempts, fallback_used, error_category.

### Patch 4 — критические тесты
- Добавлены standalone regression tests для concurrency (consume, payment, favorite), Alembic, assets, fonts, data deletion, privacy (Sentry/PostHog).

### Patch 5 — RU/EN, onboarding, «Мой Аркан», i18n
- Ключи RU/EN синхронизированы; добавлены safety, data deletion, voice errors, privacy.
- «Мой Аркан»: 6 вопросов, явная scoring matrix, tie-break к младшему аркану.
- Onboarding пересмотрен: сначала согласие, затем необязательное имя, затем дата рождения (можно пропустить); заявления о шифровании убраны.
- Голос Moira приведён к единому стилю: женский род, спокойный тон, символическая интерпретация, без обещаний сверхъестественной точности.

### Patch 6 — фоновые задачи, история, share, favorites
- Daily push: `last_push_date` обновляется только после успешной отправки; ошибки Telegram не помечают push выполненным.
- Weekly mirror защищён от дублей через `last_mirror_week` (user_id + ISO year/week).
- `_toggle_favorite` идемпотентен при параллельных вызовах.
- История, share, favorite проверяют владельца `Reading.user_id == current_user.id`.
- Share не включает исходный вопрос, дату рождения, историю, внутренние ID без отдельного действия пользователя.

### Patch 7 — observability, assets, README
- Sentry `before_send` redact exception values, request data, user PII, Authorization, токены, дату рождения, username; добавлен `correlation_id`.
- PostHog allowlist свойств.
- Fallback для шрифтов: project-local → OS → `load_default()`.
- README разделён на «Работает и проверено», «Реализовано, но экспериментально», «Известные ограничения», «Запланировано» и синхронизирован с кодом.

## Изменённые файлы

- `bot/handlers/features.py`
- `bot/handlers/reading.py`
- `bot/handlers/payment.py`
- `bot/handlers/admin.py`
- `bot/handlers/start.py`
- `bot/llm/adapter.py`
- `bot/keyboards.py`
- `bot/visual/render.py`
- `bot/services/analytics.py`
- `bot/main.py`
- `bot/db/models.py`
- `bot/i18n/locales/ru.json`
- `bot/i18n/locales/en.json`
- `tests/smoke_test.py`
- `tests/test_patch1_runtime.py`
- `tests/test_patch2_payments.py`
- `tests/test_patch3_llm.py`
- `tests/test_patch4_critical.py`
- `tests/test_patch5_i18n_quiz.py`
- `tests/test_patch6_background.py`
- `README.md`
- `docs/STABILIZATION_PLAN.md`
- `docs/STABILIZATION_REPORT.md`

## Миграции

- `0001_baseline` — базовая схема.
- `0002_growth` — payment ledger + growth tables (referrals, favorites, llm_usage, events).
- Текущая версия: `0002_growth (head)`.
- `alembic check`: `No new upgrade operations detected`.

## Добавленные тесты

1. `tests/test_patch1_runtime.py` — FSM алтаря, FSM промокода, очистка FSM, запрет voice, ошибка edge-tts, голосовая ошибка после успешного текста.
2. `tests/test_patch2_payments.py` — повторный successful payment, параллельный successful payment, повторный refund, параллельное списание одного кредита, referral один раз, self-referral, повторная активация промокода, технический сбой не забирает право.
3. `tests/test_patch3_llm.py` — LLM timeout, LLM truncation, неверное число card interpretations, встроенный fallback.
4. `tests/test_patch4_critical.py` — доступ к чужому Reading, параллельное добавление favorite, ошибка записи `llm_usage`, privacy Sentry, privacy PostHog, паритет RU/EN, Alembic upgrade на пустой базе, upgrade копии существующей БД, отсутствующий asset, отсутствующий font, удаление пользовательских данных.
5. `tests/test_patch5_i18n_quiz.py` — паритет RU/EN, тест «Мой Аркан».
6. `tests/test_patch6_background.py` — restart daily push, отсутствие дубля weekly mirror.
7. `tests/smoke_test.py` — общий smoke test.

## Результаты команд

```powershell
# Синтаксическая проверка
.venv\Scripts\python.exe -m compileall bot -q
# compileall: OK

# Миграции
.venv\Scripts\python.exe -m alembic current
# 0002_growth (head)
.venv\Scripts\python.exe -m alembic check
# No new upgrade operations detected.
# alembic check: OK

# Smoke
.venv\Scripts\python.exe tests/smoke_test.py
# ALL SMOKE TESTS PASSED

# Patch tests
.venv\Scripts\python.exe tests/test_patch1_runtime.py   # PATCH 1 TESTS PASSED
.venv\Scripts\python.exe tests/test_patch2_payments.py  # PATCH 2 TESTS PASSED
.venv\Scripts\python.exe tests/test_patch3_llm.py       # PATCH 3 TESTS PASSED
.venv\Scripts\python.exe tests/test_patch4_critical.py  # PATCH 4 CRITICAL TESTS PASSED
.venv\Scripts\python.exe tests/test_patch5_i18n_quiz.py # PATCH 5 TESTS PASSED
.venv\Scripts\python.exe tests/test_patch6_background.py # PATCH 6 TESTS PASSED
```

## Что не удалось проверить

- **End-to-end платежи Telegram Stars**: тесты используют моки; реальная оплата, refund и webhook/polling не проверялись в продакшене.
- **Реальные LLM-вызовы**: тесты используют моки и fallback; поведение с конкретной моделью `deepseek/deepseek-chat` на OpenRouter/AIGate в продакшене не воспроизводилось.
- **Реальная доставка voice/audio**: тесты проверяют fallback-логику, но не отправку в реальный Telegram.
- **Фоновые задачи в долгосрочной перспективе**: проверены unit-сценарии restart/dedup, но не многодневная работа планировщика.
- **Переносимость на Linux/VPS**: файловые пути и шрифты проверены на Windows; Linux-запуск не воспроизводился.
- **Исходная история изменений**: поскольку рабочая директория не под Git, история патчей восстановлена из `docs/STABILIZATION_PLAN.md` и текущего состояния кода.

## Оставшиеся P1/P2-задачи

- **P2**: Инициализировать Git-репозиторий и зафиксировать текущее состояние, чтобы получить reproducible baseline.
- **P2**: Провести ручное тестирование на Linux/VPS с реальным BotFather-токеном (dev-бот).
- **P2**: Проверить real-time отправку voice/audio для пользователя с отключёнными voice-notes.
- **P2**: Настроить мониторинг `bot.log` на регулярные паттерны (`coroutine was never awaited`, `IntegrityError`, `TelegramBadRequest`) после запуска.
- **P2**: Определить политику частично использованных пакетов при refund (сейчас выбрано минимально безопасное правило).
- **P2**: Добавить webhook-режим и отдельный worker при росте нагрузки (запланировано, не блокирует MVP).

## Риски запуска

- **SQLite**: один writer-процесс. Не запускать несколько инстансов бота с одной БД.
- **Фоновые задачи**: живут в процессе polling. При рестарте планировщик начинает заново; дубли предотвращаются полями `last_push_date`/`last_mirror_week`, но необходим мониторинг.
- **Сеть/LLM**: бот зависит от Telegram Bot API и внешнего LLM-endpoint. При недоступности LLM сработает fallback, но качество трактовки будет ниже.
- **TTS**: edge-tts возвращает MP3; Telegram voice note предпочитает OGG/OPUS. При запрете voice-notes бот fallback'ит на audio/текст, UX может отличаться от ожидаемого.
- **Safety-фильтр**: эвристический, не заменяет человеческую модерацию.
- **Refund**: минимально безопасное правило может отличаться от будущей бизнес-политики; требуется документация для поддержки.

## Вердикт

**Готов к закрытому тестированию при выполнении указанных условий:**

- Использовать dev-бота и dev/тестовую БД.
- Не запускать несколько инстансов на одной SQLite.
- Включить мониторинг `bot.log` на паттерны `coroutine was never awaited`, `IntegrityError`, `TelegramBadRequest`.
- Провести ручной прогон реальных платежей и voice-доставки перед публичным запуском.
- Инициализировать Git и закоммитить текущее состояние для воспроизводимости.

Критические критерии завершения (runtime, финансовая корректность, LLM fallback, privacy, i18n, миграции, тесты) выполнены.
