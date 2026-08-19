# Moira deploy kit

Артефакты для single-instance production (Linux VPS + systemd).
Полный сценарий и политика — в `docs/PRODUCTION_RUNBOOK.md`; здесь — файлы и
порядок действий одной страницей.

## Состав

| Файл | Назначение |
|---|---|
| `moira.service` | systemd-unit: один polling-процесс, restart on-failure |
| `moira-backup.sh` | online-backup SQLite (backup API) + retention 14 копий |
| `moira-restore-drill.sh` | восстановление в изолированную папку + integrity-check |

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
30 3 * * * moira MOIRA_DB_PATH=/var/lib/moira/moira.db /opt/moira/app/deploy/moira-backup.sh
```

Раз в месяц (и перед каждым обновлением) — drill:

```bash
sudo -u moira /opt/moira/app/deploy/moira-restore-drill.sh /var/backups/moira/moira-<stamp>.db
```

## Чек-лист после первого запуска

1. `journalctl -u moira -n 50` — есть `Start polling`, нет повторяющихся ошибок.
2. Ровно один процесс `bot.main`; lock-файл `.bot.runtime.lock` принадлежит ему.
3. Живой Telegram smoke из `docs/PRODUCTION_RUNBOOK.md` (RU+EN расклад, fallback,
   journal, share, delete).
4. `moira-backup.sh` отработал вручную хотя бы раз; drill прошёл.

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
