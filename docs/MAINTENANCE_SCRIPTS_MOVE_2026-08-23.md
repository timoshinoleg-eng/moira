# Moira — перенос корневых `_moira_*`-скриптов в scripts/maintenance/

Дата: 2026-08-23. Этап 1 (гигиена репо), пункт 1 плана `../HANDOFF_PROD_READINESS.md` (v2).

## Наблюдение (проверено по коду)

`docs/PRODUCTION_RUNBOOK.md` и `docs/BETA_RUNBOOK.md` **не вызывают** ни один
корневой скрипт `_moira_*` — прод-процедуры используют inline-команды и файлы
`deploy/`/`scripts/`. Все 27 корневых `_moira_*.py/.ps1`:
- gitignored (маски `_moira_*.py`, `_moira_*.ps1`);
- захардкожены на путь dev-машины `C:\Users\IMYAREK\Voprosy\moira`;
- ряд пишет evidence в `audit_moira_2026-08-22/` (protected, не трогается).

Это одноразовые P0/audit-артефакты передачи, а не прод-службы. Эквиваленты уже
отслеживаются git и используются в проде:
- Eval: `scripts/run_oracle_v6_eval.py`, `..._parallel.py`,
  `scripts/run_oracle_p0_3_adversarial_eval.py`, `scripts/create_immutable_eval_baseline.ps1`;
- Бэкап/restore: `deploy/moira-backup.sh`, `deploy/moira-restore-drill.sh`, `deploy/win_backup.py`;
- Secret-scan: заменяется на `gitleaks` (этап 2), плюс `docs/PRODUCTION_RUNBOOK.md`;
- OpenRouter-smokes: `scripts/openrouter_*`.

## Решение

Все 27 `_moira_*` **перенесены** (а не удалены) в `scripts/maintenance/`, чтобы
ничего не потерять. Удаление не выполнялось — часть скриптов семантически ценна
для верификации (backup_verify, restore_drill, secret_scan, immutable_eval,
m2 model/config probe), но как dev-артефакты git больше не интересуют (директория
`scripts/maintenance/` под маской `_moira_*`, поэтому не попадает в коммиты).

Корень репо остался с только отслеживаемыми `diag.py`, `run.ps1`, `run_bg.py`.

Решение не меняет прод-процедуры: `docs/PRODUCTION_RUNBOOK.md` и
`docs/BETA_RUNBOOK.md` не ссылались на `_moira_*` и обновлять их пути не требуется.

## Что дальше (этап 1)

- Пункт 2: uv — `pyproject.toml` + `uv.lock`.
- Пункт 3: merge `feat/moira-production-readiness` → `main`, тег `v1.0.0-rc.1`.
- Пункт 4: README статус RC + ссылка на runbook.