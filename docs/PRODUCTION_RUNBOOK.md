# Moira production runbook

## Supported small-scale topology

Moira runs as one polling process, one persistent SQLite database and one
persistent directory. Do not add a webhook, Redis, worker, PostgreSQL, or a
second bot instance for the first production release. The application owns a
non-blocking .bot.lock; a service manager remains the operational restart
and health boundary.

Example Linux layout:

~~~bash
sudo useradd --system --create-home --home-dir /opt/moira --shell /usr/sbin/nologin moira
sudo -u moira git clone https://github.com/timoshinoleg-eng/moira.git /opt/moira/app
: "${MOIRA_RELEASE_SHA:?set the approved terminal-CI commit SHA}"
sudo -u moira git -C /opt/moira/app switch --detach "$MOIRA_RELEASE_SHA"
test "$(sudo -u moira git -C /opt/moira/app rev-parse HEAD)" = "$MOIRA_RELEASE_SHA"
sudo -u moira python3 -m venv /opt/moira/app/.venv
sudo -u moira /opt/moira/app/.venv/bin/pip install -r /opt/moira/app/requirements.txt
sudo install -o moira -g moira -m 700 -d /var/lib/moira /etc/moira /var/backups/moira
sudo install -o root -g moira -m 640 /dev/null /etc/moira/moira.env
~~~

Create /etc/moira/moira.env with BOT_TOKEN, ADMIN_IDS,
DB_PATH=/var/lib/moira/moira.db, the chosen FREE_READINGS, and optional
provider/observability credentials. This file is never committed.

Deepgram voice input remains optional. Enable it only with the exact settings
and live acceptance path in `docs/DEEPGRAM_VOICE_POC.md`; the rest of Moira
continues to work with `DEEPGRAM_STT_ENABLED=false`.

Release defaults keep `LLM_RETRY_POLICY_V2=false`,
`LLM_CONTROLLED_REPAIR_ENABLED=false`, and `DEEPGRAM_STT_ENABLED=false` until
their deterministic and live capability gates pass. TTS and Stars also remain
unapproved capabilities until their independent live gates pass.

## Migrate and launch

The release schema head is `0008_push_delivery_foundation`. Application startup
verifies that exact revision and never uses SQLAlchemy `create_all()` as a
substitute for Alembic. Back up first, then run both commands before starting.

~~~bash
sudo -u moira bash -c 'set -a; . /etc/moira/moira.env; set +a; /opt/moira/app/.venv/bin/python -m alembic upgrade head'
sudo -u moira bash -c 'set -a; . /etc/moira/moira.env; set +a; /opt/moira/app/.venv/bin/python -m alembic check'
~~~

Install /etc/systemd/system/moira.service:

~~~ini
[Unit]
Description=Moira Telegram tarot bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=moira
Group=moira
WorkingDirectory=/opt/moira/app
EnvironmentFile=/etc/moira/moira.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/moira/app/.venv/bin/python -m bot.main
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
~~~

~~~bash
sudo systemctl daemon-reload
sudo systemctl enable --now moira
sudo systemctl status moira --no-pager
sudo journalctl -u moira -n 100 --no-pager
~~~

The production health check is the service state plus the real Telegram smoke;
there is no HTTP health endpoint to claim. Check that exactly one bot.main
process holds the lock and that no second instance targets the same database.

## Backup and restore

Back up before every update and nightly with the SQLite online backup API:

~~~bash
sudo -u moira /opt/moira/app/.venv/bin/python -c "import sqlite3, pathlib, datetime; src=sqlite3.connect('/var/lib/moira/moira.db'); out=pathlib.Path('/var/backups/moira') / f'moira-{datetime.datetime.now():%Y%m%d-%H%M%S}.db'; dst=sqlite3.connect(out); src.backup(dst); dst.close(); src.close(); print(out)"
~~~

Keep the backup directory on persistent storage and test a restore on an
isolated copy. To restore after a confirmed incident: stop the service, retain
the broken database as evidence, copy the chosen known-good backup to
/var/lib/moira/moira.db, preserve ownership (moira:moira, mode 600), then
start the service and run the Telegram smoke. Restore database and code from
the same known-good release when a migration was involved.

## Update and rollback

~~~bash
sudo systemctl stop moira
# run the backup command above
sudo -u moira git -C /opt/moira/app fetch origin --tags
sudo -u moira git -C /opt/moira/app switch --detach <approved-commit-or-tag>
sudo -u moira /opt/moira/app/.venv/bin/pip install -r /opt/moira/app/requirements.txt
sudo -u moira bash -c 'set -a; . /etc/moira/moira.env; set +a; /opt/moira/app/.venv/bin/python -m alembic upgrade head'
sudo -u moira bash -c 'set -a; . /etc/moira/moira.env; set +a; /opt/moira/app/.venv/bin/python -m alembic check'
sudo systemctl start moira
sudo journalctl -u moira -n 100 --no-pager
~~~

For rollback, first stop the service, restore the matching database backup,
switch to the previous approved code revision, reinstall that revision's
requirements, then start and smoke-test. Do not downgrade a live database by
guessing: use the paired backup instead.

Only a reviewed exact commit SHA with terminal CI and matching sanitized
artifact/Candidate manifests is deployable. A local branch, dirty snapshot, or
an old local RC name is not a release source. Verify `git rev-parse HEAD`
against the approved SHA before migrations and service start.

## Required release verification

Run the full preflight in BETA_RUNBOOK.md, then perform the real Telegram
smoke: /start; RU and EN readings; a real card image; LLM-off fallback;
follow-up, Journal, favourite and share; Altar; quiz; voice/audio fallback;
and /delete_my_data. If enabled, also smoke voice question → transcript edit
→ confirmed reading → voice-origin share. Record NOT TESTED — external credential required if
no safe bot token or test account is available.
