# Moira — Release Baseline 2026-08-23

Этап 0 плана `../HANDOFF_PROD_READINESS.md` (версия 2), DoD этапа 0.
Дата фиксации: 2026-08-23.

## Git

- Ветка: `release/1.0` (создана от `feat/moira-production-readiness`).
- HEAD: `386e5dec2bdf2344d26e4d0849ded6e7628dbb65` — `feat(reliability): prepare P0 production readiness RC`.
- Впереди `main`: 14 коммитов, позади 0 (RC-контент ещё не в `main`, передаётся на этапе 1).
- Рабочее дерево: чистое.

## Бэкап и восстановление (SQLite-цепочка ещё валидна)

- Свежий бэкап снят через существующий `deploy/win_backup.py`:
  `backups/moira-20260823-131514.db` (retention 14).
- Restore-drill прогнан по этому бэкапу в изолированную temp-копию (evidence:
  `docs/restore_drill_evidence_2026-08-23.json`).
  - `PRAGMA integrity_check` → `ok`
  - `alembic_version` → `0008_push_delivery_foundation`
  - обязательные таблицы `users/readings/payments/llm_usage` — все на месте,
    отсутствующих нет
  - строки: `llm_usage=177, payments=0, readings=7, users=2`
  - результат: `pass`; чувствительные содержимое строк на диск не выгружалось.
- Примечание: штатный `_moira_p0_restore_drill.py` привязан к маске `moira-p0-*.db`
  и пишет evidence в `audit_moira_2026-08-22/` (protected). Для этого baseline
  использован эквивалентный изолированный drill с записью в `docs/`.

## Тесты

- Ожидание 175 passed (источник: `HANDOFF_PROD_READINESS.md`, помечено
  «[проверено]» 2026-08-23). Отдельный прогон pytest на этом этапе не выполнялся
  (принято решение по просьбе владельца — тесты гоняются заново на этапах 1/2 в CI).

## Immutable eval

- Прогон immutable eval на этом этапе ОТЛОЖЕН по решению владельца.
- Базлайн на месте: `docs/IMMUTABLE_QUALITY_EVAL_BASELINE_2026-08-17.json`
  + контрольные суммы `.sha256`.
- Обязательный прогон против базлайна будет выполнен при первом изменении
  LLM-пайплайна и в рамках quality-гейтов этапа 5.

## DoD этапа 0

- [x] Бэкап восстановим (drill `pass`).
- [x] Ветка `release/1.0` создана от штатного RC-коммита.
- [x] Baseline-документ записан.
- [ ] Immutable eval — отложен по решению владельца (зафиксировано выше).