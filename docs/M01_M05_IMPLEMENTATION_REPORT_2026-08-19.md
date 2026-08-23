# Выполнение M-01–M-05: LLM reliability foundation

**Дата:** 19 августа 2026 г.
**Ветка:** `feat/moira-production-readiness`
**Ревизия до начала:** `d0f442b`
**Статус:** выполнено и проверено. Новая retry-политика остаётся выключенной в фактическом `.env`, поэтому активное production-поведение не меняется до явного включения флага.

## Выполненные задачи

| Задача | Результат |
|---|---|
| M-01 | Создан `docs/M01_BASELINE_2026-08-19.md`. Зафиксированы исходная ветка, наличие пользовательских незакоммиченных изменений, baseline `154 passed in 12.98s` и release guard. |
| M-02 | Спроектирована совместимая схема telemetry: provider hostname, attempts, fallback flag, error category, timeout stage и opaque request id. Добавлены feature flag и ограниченные timeout/attempt конфигурации. |
| M-03 | Создана миграция `0006_llm_reliability_telemetry`, расширены ORM-модель и allowlist аналитики, сохранение telemetry подключено к `_log_usage()`. Миграция проверена на временной SQLite-базе в цикле upgrade → downgrade → upgrade и применена к `moira.db`. |
| M-04 | Добавлена строгая error taxonomy и `AsyncRetrying` policy: retry допускается только для timeout, 429, сетевых, 5xx, schema/identity и privacy ошибок; 401/403, прочие 4xx, конфигурационные и неизвестные ошибки не повторяются. |
| M-05 | Введён изолированный V2-путь `interpret_reading()` под `LLM_RETRY_POLICY_V2`. Он ограничен двумя попытками, имеет отдельный primary timeout и общий total latency budget, выбирает backup model только на второй попытке и пишет безопасную telemetry. Старый путь сохранён без изменения и остаётся рабочим по умолчанию. |

## Реализация

| Область | Изменения |
|---|---|
| Конфигурация | Добавлены `LLM_RETRY_POLICY_V2=false`, `LLM_V2_PRIMARY_TIMEOUT_SEC=12`, `LLM_V2_TOTAL_TIMEOUT_SEC=18`, `LLM_V2_MAX_ATTEMPTS=2` в `.env.example` и `Config`. Количество попыток жёстко ограничено диапазоном 1–2. |
| Зависимости | `tenacity>=9.0,<10.0` закреплён как прямая зависимость. |
| Telemetry | `LlmUsage` и revision `0006` получили `provider`, `attempts`, `fallback_used`, `error_category`, `timeout_stage`, `request_id`, индексы по `(status, created_at)` и `(model, created_at)`. |
| Privacy | В telemetry сохраняется только hostname provider URL; credentials и path отбрасываются. В базе и событиях не сохраняются вопрос, prompt, raw completion, интерпретация или Telegram PII. |
| Retry | `AsyncRetrying` использует максимум две попытки, exponential jitter до 1 секунды и `reraise=True`; общий `asyncio.timeout` предотвращает превышение total latency budget. |
| Shutdown | Добавлен `close_db()` и его штатный вызов в `bot/main.py`; это устранило предупреждение `Event loop is closed` из полного pytest-прогона. |

## Проверки

| Проверка | Результат |
|---|---|
| Baseline до работ | `154 passed in 12.98s` |
| Новые retry/schema/config/trust boundary тесты | `38 passed in 4.61s` на промежуточной проверке |
| V2 retry-политика | 18 тестов: taxonomy, retry/no-retry, opaque request id, backup on 429, no retry on auth, telemetry persistence, feature-flag entrypoint, sanitisation provider URL |
| Миграция на временной SQLite | Успех: `upgrade head → downgrade 0005_growth_attribution → upgrade head` |
| Применённая ревизия рабочей БД | `0006_llm_reliability_telemetry (head)` |
| Финальный полный pytest | `174 passed in 16.37s`, без предупреждений |
| Проверка diff | `git diff --check` завершилась без ошибок |

## Резервная копия и rollback

Перед миграцией создана копия текущей базы:

```text
backups\moira-pre-0006-20260819-200752.db
```

Для отката schema при выключенном боте можно применить:

```powershell
.\.venv\Scripts\alembic.exe downgrade 0005_growth_attribution
```

Функциональный rollback проще и безопаснее: оставить/установить `LLM_RETRY_POLICY_V2=false`. В этом состоянии приложение использует сохранённый прежний LLM-путь, а новые nullable telemetry columns не влияют на поведение.

## Рекомендуемый rollout

1. Запустить staging с `LLM_RETRY_POLICY_V2=true` и указанными default budget values.
2. Наблюдать 7–14 дней: success/fallback rate, attempts, error category, p95 latency, token usage и долю backup model.
3. Сравнить с baseline; не включать production, если p95 ухудшился более чем на 20% или увеличилась стоимость successful reading без доказанного роста success rate.
4. При успешном cohort rollout включить флаг на production. При аномалии немедленно вернуть `false`; миграция БД для этого не откатывается.

## Изменённые/добавленные файлы M-01–M-05

```text
.env.example
requirements.txt
bot/config.py
bot/db/__init__.py
bot/db/database.py
bot/db/models.py
bot/llm/adapter.py
bot/main.py
bot/services/analytics.py
alembic/versions/0006_llm_reliability_telemetry.py
tests/test_llm_config.py
tests/test_llm_retry_policy.py
docs/M01_BASELINE_2026-08-19.md
docs/M01_M05_IMPLEMENTATION_REPORT_2026-08-19.md
```

Существующие пользовательские незакоммиченные изменения не очищались, не восстанавливались и не коммитились.
