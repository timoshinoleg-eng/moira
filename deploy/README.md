# Moira deploy kit

Артефакты для single-instance production (Linux VPS + systemd).
Полный сценарий и политика — в `docs/PRODUCTION_RUNBOOK.md`; здесь — файлы и
порядок действий одной страницей.

## Состав

| Файл | Назначение |
|---|---|
| `moira.service` | systemd-unit: один polling-процесс, restart on-failure |
| `backup_restore.py` | единое fail-closed ядро backup/verify/restore/rollback |
| `moira-backup.sh` | online-backup + hash manifest + release SHA + retention |
| `moira-restore-drill.sh` | изолированный restore/rollback + Alembic/app/read checks |

## Bootstrap VPS (однократно)

```bash
sudo useradd --system --create-home --home-dir /opt/moira --shell /usr/sbin/nologin moira
: "${MOIRA_RELEASE_SHA:?set the approved terminal-CI commit SHA}"
sudo -u moira git clone https://github.com/timoshinoleg-eng/moira.git /opt/moira/app
sudo -u moira git -C /opt/moira/app switch --detach "$MOIRA_RELEASE_SHA"
test "$(sudo -u moira git -C /opt/moira/app rev-parse HEAD)" = "$MOIRA_RELEASE_SHA"
sudo -u moira python3 -m venv /opt/moira/app/.venv
sudo -u moira /opt/moira/app/.venv/bin/pip install -r /opt/moira/app/requirements.txt
sudo install -o moira -g moira -m 700 -d /var/lib/moira /etc/moira /var/backups/moira
sudo install -o root -g moira -m 640 /dev/null /etc/moira/moira.env
# заполнить /etc/moira/moira.env по шаблону .env.example (DB_PATH=/var/lib/moira/moira.db)

sudo -u moira bash -c 'set -a; . /etc/moira/moira.env; set +a; \
  cd /opt/moira/app && .venv/bin/python -m alembic upgrade head && .venv/bin/python -m alembic check'

sudo install -m 644 moira.service /etc/systemd/system/moira.service
sudo systemctl daemon-reload && sudo systemctl enable --now moira
sudo systemctl status moira --no-pager
```

Ночной бэкап — строка в `/etc/cron.d/moira-backup`:

```
30 3 * * * moira MOIRA_DB_PATH=/var/lib/moira/moira.db MOIRA_APP_DIR=/opt/moira/app MOIRA_BACKUP_RPO_SECONDS=86400 /opt/moira/app/deploy/moira-backup.sh
```

Перед каждым обновлением сначала выполнить backup от SHA текущего deployed
release. Команда создаёт `.db` и обязательный `.manifest.json`, проверяет hash,
integrity, foreign keys, Alembic revision, `payments`, Journal и entitlement
reads, затем применяет retention только к валидным именованным парам:

```bash
CURRENT_SHA="$(sudo -u moira git -C /opt/moira/app rev-parse HEAD)"
sudo -u moira env MOIRA_RELEASE_SHA="$CURRENT_SHA" \
  /opt/moira/app/deploy/moira-backup.sh /var/backups/moira
```

Раз в месяц и перед release — restore drill в новый каталог:

```bash
BACKUP=/var/backups/moira/moira-<stamp>.db
sudo -u moira /opt/moira/app/deploy/moira-restore-drill.sh \
  "$BACKUP" "$CURRENT_SHA" /var/lib/moira-restore-drills/<run-id>
```

Rollback drill использует backup, созданный **до обновления** и связанный с
предыдущим SHA. Подготовить отдельный exact checkout предыдущего SHA и запустить
тот же wrapper с `MOIRA_RESTORE_OPERATION=rollback-drill` и соответствующими
`MOIRA_APP_DIR`/`MOIRA_PYTHON`; `MOIRA_TOOL_APP_DIR` указывает на current
recovery tooling, поэтому предыдущий checkout не обязан содержать новый script.
Live database и service drill не затрагивает.
Report содержит измеренные recovery-point age и RTO; controlled Telegram smoke
остаётся отдельной внешней проверкой.

## Чек-лист после первого запуска

1. `journalctl -u moira -n 50` — есть `Start polling`, нет повторяющихся ошибок.
2. Ровно один процесс `bot.main`; lock-файл `.bot.runtime.lock` принадлежит ему.
3. Живой Telegram smoke из `docs/PRODUCTION_RUNBOOK.md` (RU+EN расклад, fallback,
   journal, share, delete).
4. `moira-backup.sh` создал hash-bound manifest; restore и rollback drills прошли.

## Переходный вариант до VPS (локальная Windows-машина)

Не является production-топологией, но допустим для invite-only beta:

- запуск через Планировщик задач от имени текущего пользователя:
  `python -m bot.main` из папки проекта (рабочая директория = корень репо);
- задача «при сбое — перезапуск», задержка 30 с;
- бэкup: `python deploy\win_backup.py` тем же планировщиком nightly;
- машина не должна уходить в сон (powercfg /change standby-timeout-ac 0).

## Важно

- Никогда не запускай второй инстанс против той же БД (SQLite, один writer).
- Разворачивай только reviewed exact SHA с terminal CI и совпавшим artifact
  manifest; branch name, dirty snapshot и старые локальные RC-имена не подходят.
- Перед `alembic upgrade` на живой базе — свежий бэкап и остановленный сервис.
- `.env` на VPS не существует — только `/etc/moira/moira.env` (root:moira 640).
- `/var/backups/moira` должен принадлежать `moira:moira` и иметь mode `700`;
  backup/manifest — `600`. Production command fail-closed при более широком mode.
- Backup и restore reports содержат только counts/hashes/timing, но сами `.db`
  являются private data и никогда не входят в Git/CI artifacts.
