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
