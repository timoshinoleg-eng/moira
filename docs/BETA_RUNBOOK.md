# Moira invite-only beta runbook

## Scope and success boundary

Use one Telegram polling instance and a persistent SQLite file. The beta is
intentionally generous enough to learn from real use: set FREE_READINGS=10
in the environment for invitees, then watch completed readings and feedback
before changing the limit. The application shows the remaining free balance
after every reading and presents the Stars tariffs before a paid path.

Do not put secrets, databases, rendered artifacts, or a local card folder
outside this repository into the beta path. The complete 78-card deck, fonts,
and provenance manifest are tracked.

## Fresh setup

~~~powershell
git clone https://github.com/timoshinoleg-eng/moira.git
cd moira
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
~~~

Set only the values appropriate to the operator:

~~~env
BOT_TOKEN=<BotFather token>
ADMIN_IDS=<operator Telegram numeric ID>
DB_PATH=moira.db
FREE_READINGS=10
# OPENROUTER_API_KEY may stay empty: the local fallback is a supported beta mode.
~~~

Never paste the token into a chat, command history, or a Git remote URL.

## Preflight

~~~powershell
.venv\Scripts\python.exe -m compileall bot
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m alembic check
.venv\Scripts\python.exe tests\test_cards_78.py
.venv\Scripts\python.exe -m pytest -q
~~~

assets/cards/manifest.json must contain 78 unique local SHA-256 values and
the cards test must report no missing assets. The .bot.lock guard prevents a
second process using the same checkout; do not run a second polling instance
against its SQLite file.

## Launch and pilot smoke

~~~powershell
.venv\Scripts\python.exe -m bot.main
~~~

With a non-paid test account, verify in both RU and EN:

1. /start, all three spread prompts, and remaining-free-count text.
2. A reading with OPENROUTER_API_KEY empty: real image, position/orientation,
   question-aware fallback, follow-up, favourite, feedback, Journal reopen and
   share card.
3. Altar, daily card, quiz, voice-to-audio fallback, and /delete_my_data.
4. A normal LLM reading if a provider key is intentionally configured.

Record a live Telegram result as PASS only when the actual Bot API conversation
was completed. Unit tests and mocked messages do not replace this smoke.

## Pilot gate

Invite 10–20 people. Hold the public opening until there are at least 30
completed readings, no lost free/paid credits after a crash, no repeated
critical error, and feedback plus qualitative comments to review. Keep
questions out of analytics; events retain only the reading ID, spread,
response mode, and positive/negative feedback.

## Failure handling

- LLM unavailable: deliver the deterministic fallback; do not consume another
  credit.
- TTS unavailable or Telegram voice forbidden: the text and saved reading
  continue, then the bot tries audio and finally sends a localized notice.
- Optional analytics unavailable: the reading continues; event persistence is
  best-effort.
- Missing assets or failed migrations: do not launch; repair the repository or
  database first.
