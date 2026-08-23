# Выполнение M-06–M-07: controlled repair и push delivery foundation

**Дата:** 19 августа 2026 г.
**Ветка:** `feat/moira-production-readiness`
**Статус:** реализовано, миграции применены, feature flags выключены по умолчанию.

## Резюме

M-06 добавляет безопасный controlled repair как строго ограниченную вторую попытку V2 LLM-пути. Repair запускается только после `validation` или `privacy` ошибки, не увеличивает предел двух внешних вызовов и строит новый payload исключительно из данных расклада и категории локальной ошибки. Он не передаёт вопрос пользователя, память прошлых чтений, raw provider output или текст исключения.

M-07 добавляет независимую от scheduler foundation для персональных ежедневных push: IANA timezone, `HH:MM` local time, следующее UTC-время и durable delivery journal. Таблица delivery не хранит message text, question, reading body или Telegram PII. Её unique key `(user_id, kind, local_period)` является защитой от duplicate delivery.

> Production-поведение пока не меняется. `LLM_CONTROLLED_REPAIR_ENABLED` отсутствует в фактическом `.env`, поэтому repair не активен. V2 push preferences стартуют как `push_enabled=false`, а существующий legacy `daily_push` не изменён. Пользовательский UI и APScheduler worker относятся к M-08/M-09.

## M-06 — выполненные изменения

| Область | Реализация |
|---|---|
| Feature flag | Добавлен `LLM_CONTROLLED_REPAIR_ENABLED=false` в `Config` и `.env.example`. Он требует уже существующий V2 retry path, но не меняет legacy-путь. |
| Eligibility | Repair возможен только для категорий `validation` и `privacy`. Auth, configuration, 4xx, unknown, network, rate limit и 5xx используют обычную bounded retry policy или controlled fallback. |
| Privacy boundary | `_build_controlled_repair_messages()` передаёт только expected card identities, positions, symbols, format/quality rules и bounded error category. В него не попадают question, recent-reading memory, raw completion и free-form exception message. |
| Call budget | Repair используется лишь на попытке №2; общее число provider calls остаётся `≤2`, общий `asyncio.timeout` остаётся прежним. Backup model выбирается на второй попытке по существующему правилу. |
| Telemetry | Добавлен безопасный булев агрегат `repair_used` в `LlmUsage`, evidence record и analytics allowlist. Содержательный repair payload не сохраняется. |
| Тесты | `tests/test_llm_controlled_repair.py`: safe payload, отсутствие private fragments, exactly-two-calls, primary→backup repair, transient retry без repair. |

### Результат benchmark и release decision

Текущий benchmark является **детерминированным contract benchmark**: он подтверждает, что malformed JSON первой попытки приводит к успешному valid second repair response, а transient 429 сохраняет обычный повтор. Это подтверждает корректность routing и privacy contract на фиксированных synthetic cases.

Фактический provider-quality benchmark с `quality_eval_24.json` не запускался, потому что он потребует внешних LLM-вызовов и расхода provider quota. Поэтому решение о production enable остаётся **не принято**. До staging-оценки флаг должен оставаться `false`.

| Gate для staging enable | Статус |
|---|---|
| Ноль question/memory/raw-output в repair payload | Пройден unit snapshot contract |
| Не более двух provider calls | Пройден integration contract |
| Backup repair после schema failure | Пройден integration contract |
| Fixed real-provider success/fallback, p95 и token-cost comparison | Требуется staging run |
| Privacy/identity hard failures на real fixed eval | Требуется staging run; блокирует enable при любом дефекте |

## M-07 — выполненные изменения

| Область | Реализация |
|---|---|
| User preferences | Добавлены `push_enabled`, `push_timezone`, `push_local_time`, `next_push_at_utc`. Новые поля nullable/disabled by default, не переводят legacy users в opt-in автоматически. |
| Delivery journal | Добавлена `PushDelivery` / `push_deliveries`: `kind`, `local_period`, `scheduled_at`, status, claim/lease/sent timestamps, attempt count и safe error code. |
| Idempotency | `UNIQUE(user_id, kind, local_period)` и SQLite `INSERT … ON CONFLICT DO NOTHING` гарантируют один плановый delivery row на local period. |
| Atomic state machine | Реализованы `plan_delivery`, `claim_delivery`, `mark_delivery_sent`, `mark_delivery_failed`, `recover_expired_claims`. Network side effect в этом модуле отсутствует; M-09 worker выполнит send вне DB transaction. |
| Timezone/DST | Используются `zoneinfo` + `tzdata` как явная runtime dependency. Wall-time policy: ambiguous fall-back использует первый occurrence; spring-forward gap сдвигается до первого валидного local minute. |
| Tests | `tests/test_push_delivery.py`: validation, RU/EN-relevant time formatting input, DST gap/fold, next UTC instant, unique planning, exactly-one claim, sent terminal state, expired lease recovery и terminal cancellation. |

## Миграции и резервная копия

| Revision | Назначение | Статус |
|---|---|---|
| `0007_controlled_repair_telemetry` | `llm_usage.repair_used` | Применена |
| `0008_push_delivery_foundation` | V2 user preferences и `push_deliveries` | Применена |

Рабочая база находится на `0008_push_delivery_foundation (head)`. Перед применением создана резервная копия:

```text
backups\moira-pre-0008-20260819-215002.db
```

Миграции успешно прошли на временной SQLite-базе цикл `upgrade head → downgrade 0006_llm_reliability_telemetry → upgrade head`.

## Итоговые проверки

| Проверка | Результат |
|---|---|
| M-06 focused tests | Пройдено |
| M-07 timezone/DST/state-machine tests | `5 passed` |
| M-06 + M-07 focused suite | `26 passed` до расширения полного набора |
| Финальный полный pytest | `183 passed in 14.78s` |
| `git diff --check` | Пройдено без ошибок |
| Рабочая Alembic revision | `0008_push_delivery_foundation (head)` |

## Изменённые и добавленные файлы

```text
.env.example
requirements.txt
bot/config.py
bot/db/__init__.py
bot/db/models.py
bot/llm/adapter.py
bot/services/analytics.py
bot/services/push_delivery.py
alembic/versions/0007_controlled_repair_telemetry.py
alembic/versions/0008_push_delivery_foundation.py
tests/test_llm_config.py
tests/test_llm_controlled_repair.py
tests/test_push_delivery.py
docs/M06_M07_IMPLEMENTATION_REPORT_2026-08-19.md
```

## Следующие действия

1. **M-06 staging decision:** выполнить fixed `quality_eval_24.json` дважды с repair off/on на согласованной модели, сравнить schema/privacy success, fallback rate, p95 and tokens. Включать `LLM_CONTROLLED_REPAIR_ENABLED=true` только при успешном gate.
2. **M-08:** построить explicit opt-in UI для timezone/time, не меняя автоматически legacy `daily_push` users.
3. **M-09:** добавить APScheduler reconciliation и bounded worker поверх уже готового delivery journal; не вводить per-user jobs, Redis или очередь до измеренного bottleneck.

Rollback функциональности: оставить оба feature flag выключенными. Schema rollback после остановки бота доступен последовательным `alembic downgrade 0006_llm_reliability_telemetry`; безопаснее обычно не откатывать additive columns, а отключать новые paths флагами.
