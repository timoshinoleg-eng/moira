# Changelog

Заметные изменения Moira. Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/);
проект следует семантическому версионированию.

## [1.0.0-rc.2] — 2026-09-27

Закрытие код-контура перед продакшном: приватность, качество кода, зависимости.

### Fixed
- **Приватность:** `/delete_my_data` теперь удаляет `reading_feedback` и `push_deliveries`
  (ранее после «удаления данных» оставались строки, привязанные к Telegram ID).
  Добавлен регрессионный тест. (#16)
- `agent_core/runtime/loop.py`: исправлена аннотация `AttentionTransition` → `AttentionState`.
- `agent_core/state/behavior.py`: добавлен недостающий импорт `Any`.
- Удалены неиспользуемые импорты в `bot/`, `agent_core/`, `scripts/`.

### Changed
- **CI:** lint стал блокирующим на правилах pyflakes (`F`) для продакшн-кода
  (`bot/`, `agent_core/`, `scripts/`); полный стилевой чек — advisory. (#21)
- **Зависимости:** `asyncpg` добавлен в `requirements.txt`; dev-пины выровнены с
  `pyproject.toml` (`pytest`, `pytest-asyncio`, `testcontainers`); `ruff==0.9.10`
  закреплён в dev-группе. (#22)

## [1.0.0-rc.1]

Первый release candidate: двуязычный таро-бот (RU/EN), Stars-платежи, личный алтарь,
тест «Мой Аркан», рефералы, голосовые вопросы, визуальная система.
Базлайн: `docs/RELEASE_BASELINE_2026-08-16.md`.
