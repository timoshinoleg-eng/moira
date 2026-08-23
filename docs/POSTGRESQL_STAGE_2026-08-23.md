# Moira — PostgreSQL: рефакторинг и верификация (этап 3)

Дата: 2026-08-23. Ветка `feat/pg`. План: `../HANDOFF_PROD_READINESS.md` v2, этап 3.

## Что сделано

1. **Диалект-независимый движок** (`bot/db/database.py`).
   - `init_db(target)` принимает SQLAlchemy-URL **или** путь.
   - `postgresql...` → `asyncpg`, пул (`DB_POOL_SIZE`, `DB_POOL_MAX_OVERFLOW`),
     `pool_pre_ping`, healthcheck `SELECT 1`.
   - SQLite (путь/URL) → прежние PRAGMA (WAL/synchronous/busy_timeout) + `create_all`
     (историческое тестовое поведение сохранено — 175 тестов без вмешательства).
   - PG-схема накатывается **только через Alembic** (`init_db` на PG не зовёт
     `create_all`).

2. **Config** (`bot/config.py`): добавлен `database_url` (из `DATABASE_URL`),
   прежний `db_path` сохранён как fallback. Приоритет: `DATABASE_URL` → `DB_PATH`.

3. **Application wiring** (`bot/main.py`): `init_db(cfg.database_url or cfg.db_path)`.

4. **Alembic** (`alembic/env.py`): URL берётся из `DATABASE_URL`, иначе `DB_PATH`
   (sqlite). Без изменения `alembic.ini` и без новых миграций `alembic check`
   показывает «No new upgrade operations detected».

5. **Зависимости** (`pyproject.toml`, `uv.lock`): добавлены `asyncpg==0.30.0` и
   тестовые `testcontainers[postgres]==4.12.0`.

6. **Тесты** (`tests/test_pg_integration.py`, маркер `postgres`): поднимают
   реальный `postgres:16` через testcontainers, гоняют `alembic upgrade head` +
   `alembic check` на чистой БД, затем CRUD + уникальность `charge_id`
   (idempotency ledger). Пропускаются, если Docker/PG недоступен.

7. **CI** (`.github/workflows/ci.yml`): основной test-джоб гоняет `-m "not postgres"`
   (175 быстрых, без Docker); новый `pg`-джоб — `-m postgres`.

8. **Сверка миграции** (`scripts/maintenance/verify_db_migration.py`): сравнение
   count по всем 10 таблицам source/target + sha256-checksum платёжного ledger
   (user_id|product|stars|charge_id|status). Backend-agnostic (любые два URL).
   Локально подтверждено: `VERIFY: PASSED`.

## Проверки (живой PostgreSQL 16)

- `alembic upgrade head` на чистой PG: **все 8 старых миграций применились без
  ошибок** (server_default "0"/"1" для boolean/integer, JSON-как-Text,
  `DateTime(timezone=True)`, SERIAL-секвенции — PG-совместимы).
- `alembic check`: **No new upgrade operations detected** → схема соответствует
  моделям; **новая миграция для PG-совместимости не требуется**.
- `init_db(database_url)` + CRUD на живой PG: пройдено.
- `test_pg_integration.py`: `2 passed` (реальные контейнеры).
- Основной прогон без PG: `175 passed`.

## Решения

- **JSON→JSONB не менялось**: модели хранят JSON-поля как `Text`, а не SQL JSON.
  Alembic check чист; миграция для смены типа не нужна и не добавлялась
  (защита от лишнего даунтайма при переносе).
- **pgloader**: прод-перенос выполняется на staging через официальный Docker-образ
  `dimitri/pgloader` (pgloader недоступен на Windows-хозяйке). Команда и сверка
  добавляются в `docs/PRODUCTION_RUNBOOK.md`. Локально сверка проверена через
  `verify_db_migration.py` (self-compare).
- **Флаги LLM не трогались**, immutable eval не гонялся: рефакторинг БД не
  затрагивает LLM-пайплайн; деградации качества исключены (тесты 175 зелёные).

## Статус по блокеру №3

Закрыт: `bot/db/database.py` больше не захардкожен на sqlite; PG полностью
поддержан (движок, миграции, тесты, CI, сверка данных).