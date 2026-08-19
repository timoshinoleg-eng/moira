# Moira Beta Readiness Report — 2026-08-16

## Decision

**Decision: NO-GO for invite-only beta at this time.** The current release candidate is traceable and its automated gates are green, but the beta prerequisites require real Telegram E2E and a valid live LLM-vs-fallback quality gate. Those two external gates are not complete.

**Current RC SHA:** `a1ed7767e615d03d31858f3e2897432b3f9755b9`.
**Automated regression:** `116 passed`.
**Fresh RC regression before quality-evidence commit:** `115 passed`; the one-test difference is explicitly explained in `RELEASE_BASELINE_2026-08-16.md` because the obsolete duplicate-router keyboard test was removed during active-routing normalization and a quality-fixture regression test was then added.

## Gate summary

| Gate | Status | Evidence | Blocker / decision |
|---|---|---|---|
| TASK 0 baseline | PASS | `docs/RELEASE_BASELINE_2026-08-16.md`; HEAD `ea9dea0…`; 78 tracked card images; one active `cb_invite` | Historical c13 issues are not carried forward without reproduction. |
| TASK 1 RC | PASS | Local commits; current SHA `a1ed776…`; `.moira-video-analysis/` remains explicitly non-release | No public push/deploy performed. |
| TASK 2 fresh install | PASS | New venv, declared dependencies, migrations `0`, `alembic check` `0`, clean RC `115 passed`, 78/78 card test and content tests pass | Full current suite is `116 passed` after quality fixture regression was added. |
| TASK 3 live Telegram E2E | BLOCKED | Read-only `getMe` HTTP 200 for `MoiraOraclebot`; no controlled user account | Need controlled owner-provided test account and privacy-safe screenshots/logs. |
| TASK 4 blind quality evaluation | BLOCKED_EXTERNAL_PROVIDER | 24 unique fixtures; fallback grounding/synthesis/reflection 24/24; hard fails 0; LLM smoke returned empty response twice | Provider path must produce one valid structured response before comparison; no score invented. |
| TASK 5 Journal/continuation | DEFERRED_GATE_A_BLOCKED | Existing automated coverage is retained | Execute after TASK 3/4 pass; no architectural expansion. |
| TASK 6 mobile visual QA | DEFERRED_GATE_A_BLOCKED | Desktop/static asset checks only | Real iOS/Android access is required for PASS. |
| TASK 7 reliability | DEFERRED_GATE_A_BLOCKED | Fresh migrations and tests pass | Backup/restore, second-instance and reconnect evidence still required. |
| TASK 8 live voice | DEFERRED_GATE_A_BLOCKED | Credentials exist in local `.env`, no live audio run performed | Run only under controlled test account and preserve privacy. |
| TASK 9 referral E2E | DEFERRED_GATE_A_BLOCKED | One active `payment.py` handler; helper-only `growth.py`; targeted tests pass | Requires fresh-account deeplink interaction. |
| TASK 10 Stars/refund | DEFERRED_P2 | Timed-pass copy corrected; no live payment action performed | Requires allowed test payment path. |
| TASK 11 video drafts | DEFERRED_P2 | Two video audit reports and growth playbook exist | Prepare drafts after product proof from TASK 3; do not publish automatically. |
| TASK 12 beta 10–20 users | NO-GO | Prerequisites not satisfied | Do not open cohort yet. |

## What is ready

The release candidate now has a cleanly traceable local commit history, a reproducible fresh install, migrations from an empty database, a complete 78-card asset set, a single active invite route, a privacy-safe referral helper, localized value-led paywall copy, and a 24-case quality fixture. Automated tests pass at 116.

## What must happen next

1. Obtain a dedicated controlled Telegram test account and run the synthetic RU/EN checklist without touching public users or production-like data.
2. Fix or replace the configured LLM provider path until a single synthetic structured response is returned. Then run the same 24 fixtures against LLM and fallback, blind the mode labels, and complete owner rubric review.
3. Run backup/restore and single-instance evidence before considering TASK 7 PASS.
4. Re-evaluate the beta gate only after TASK 0–4, TASK 5, TASK 7 and TASK 9 satisfy their acceptance criteria. The beta cohort must remain limited to 10–20 controlled users; no public launch is authorized by this report.
Continuation 2026-08-16: Gate A remains NO-GO. TASK 3 is BLOCKED pending controlled Telegram test account; TASK 4 is BLOCKED pending provider availability. Gate B and TASK 12 remain deferred.
Fallback continuation 2026-08-16: provider resilience improved with primary-first backup model routing. This does not by itself close TASK 3 or TASK 4; no beta/public launch was performed.
Telegram runtime continuation: no local duplicate process or stale lock remains. Current polling process is alive with bounded retry, but Telegram Bot API returns HTTP 502 Bad Gateway; live E2E and beta remain blocked.
Additional local evidence: TASK 2 fresh install/regression rechecked after latest changes; isolated pytest 116 passed and ASCII-path fresh migrations/check passed. TASK 3 remains dependent on stable Telegram Bot API and controlled account evidence.
Current decision remains NO-GO. Local gates are green, but Telegram Bot API availability is intermittent from the runtime host and live E2E is not repeatably evidenced. TASK 11 draft and TASK 6 checklist are prepared; no publication or cohort launch occurred.
Quality improvement continuation: Oracle prompt v6 now explicitly requires clear natural prose with restrained mystical imagery and rejects gibberish/pseudo-esoteric filler. Regression is green, but live quality evaluation and Telegram E2E remain blocked by unstable external Bot API/provider evidence.
Oracle v6 continuation: provider key precedence, JSON-mode routing, mystical voice contract, schema alignment and representative synthetic checks were repaired and validated. Full 24-case live-provider gate remains BLOCKED; no beta decision changes.

## Continuation — final runtime and quality recheck

The bot was restarted successfully after recovery from an unreleasable legacy Windows lock. A single current polling process is alive under the versioned `.bot.runtime.lock`, with prompt `v6-mystical-clear`, JSON-mode primary/backup routing, and the configured OpenRouter key available without disclosure. This is runtime availability evidence only and does not replace user-flow E2E evidence.

The complete regression suite now returns **119 passed**. A post-restart sequential synthetic questionnaire completed successfully: the RU base result and RU/EN question-lens results were structured; the recorded non-content checks confirm card grounding, restrained mystical imagery, and absence of gibberish markers. No real user content was captured.

A new full 24-case blind run at concurrency two was attempted. The free provider repeatedly returned malformed JSON, empty replies, truncated JSON, and a schema-overlength field during retries. The run was stopped after sustained transient failure; no partial result is treated as a completed comparison. **TASK 4 remains BLOCKED_EXTERNAL_PROVIDER** for the full provider-evidence criterion. **TASK 3 remains BLOCKED** until the owner supplies the requested controlled Telegram E2E PASS/FAIL checklist. Accordingly, **TASK 12 remains NO-GO** and no publication or invite-only cohort has been started.
