# Moira — MANUS Execution Log — 2026-08-16

## TASK 0 — Normalize baseline and snapshots

**Status:** PASS.  
**Evidence:** Current HEAD before RC `ea9dea0dd694bd934bc958d67fbb34482ef0641f`; 78 tracked card images; migrations `0002_growth` through `0005_growth_attribution`; current test collection explained in `docs/RELEASE_BASELINE_2026-08-16.md`; `payment.py` is the sole active `cb_invite` owner.  
**Files changed:** `docs/RELEASE_BASELINE_2026-08-16.md`, `bot/handlers/growth.py`, `bot/handlers/payment.py`, `bot/keyboards.py`, `bot/main.py`, `tests/test_growth_invite.py`.  
**Regression:** Targeted growth/payment/product tests `12 passed`; current full suite later `116 passed`.  
**Decision:** Removed duplicate growth router; retained helper-only module and existing payment route.  
**Blocker:** None for baseline.

## TASK 1 — Release candidate

**Status:** PASS.  
**Evidence:** Local RC commits; current SHA `a1ed7767e615d03d31858f3e2897432b3f9755b9`; `.moira-video-analysis/` remains explicitly outside release artifact.  
**Files changed:** Release code, locales, tests and docs are committed; no `.env`, DB, secrets or signed URLs staged.  
**Regression:** `git diff --check` clean for runtime changes; Markdown hard-break trailing spaces are intentional documentation formatting.  
**Decision:** No push or public deployment.  
**Blocker:** None for local RC.

## TASK 2 — Fresh install and regression

**Status:** PASS.  
**Evidence:** New `moira_task2_venv`; declared dependencies installed; empty SQLite `alembic upgrade head` exit `0`; `alembic check` exit `0`; clean RC `115 passed`; current worktree `116 passed`; `assets/cards` count `78`; manifest and `PROVENANCE.md` present; card/content subset `61 passed`.  
**Files changed:** No additional runtime changes; evidence is documented in `RELEASE_BASELINE` and `BETA_READINESS`.  
**Regression:** One-test difference from 116 reference was explained: obsolete duplicate-router keyboard test removed, then quality-fixture regression test added; current suite is 116.  
**Decision:** Fresh install gate PASS.  
**Blocker:** None.

## TASK 3 — Real Telegram E2E

**Status:** BLOCKED_EXTERNAL_ACCOUNT.  
**Evidence:** Read-only Telegram `getMe` returned HTTP 200 and bot identity `MoiraOraclebot`; no controlled test account was available.  
**Files changed:** `docs/LIVE_GATE_REPORT_2026-08-16.md`.  
**Regression:** Local automated checks pass; no live user flow claimed.  
**Decision:** Do not simulate or mark RU/EN result/history/follow-up/share/delete as PASS.  
**Blocker:** Dedicated controlled Telegram account and privacy-safe screenshots/logs.

## TASK 4 — Blinded LLM vs fallback quality

**Status:** BLOCKED_EXTERNAL_PROVIDER.  
**Evidence:** `tests/fixtures/quality_eval_24.json` contains 24 unique cases covering RU/EN × 3 spreads × 4 profiles; fallback card grounding, synthesis and reflection are 24/24; hard-fail heuristic 0. Live one-case LLM smoke returned empty response twice and `LLM_RESULT_AVAILABLE=False`.  
**Files changed:** `tests/fixtures/quality_eval_24.json`, `tests/test_quality_eval_fixture.py`, `docs/QUALITY_EVAL_2026-08-16.md`.  
**Regression:** Full current suite `116 passed`; quality fixture test included.  
**Decision:** No LLM score invented and no independent judge claim made.  
**Blocker:** Provider/configuration returns empty response.

## TASK 5 — Continuation and Journal

**Status:** DEFERRED_GATE_A_BLOCKED.  
**Evidence:** Existing automated continuation/history coverage retained; no note schema added.  
**Files changed:** None beyond prior RC changes.  
**Regression:** Included in current full suite.  
**Decision:** Do not add Journal note until live core chain is verified; avoid architecture expansion.  
**Blocker:** Gate A TASK 3/4.

## TASK 6 — Mobile visual QA

**Status:** DEFERRED_GATE_A_BLOCKED.  
**Evidence:** Static assets and content pass; no real iOS/Android access.  
**Files changed:** None.  
**Regression:** Card/content subset `61 passed`.  
**Decision:** Desktop/Pillow preview is not marked mobile PASS.  
**Blocker:** Real device/access requirement.

## TASK 7 — Backup/restore and runtime reliability

**Status:** DEFERRED_GATE_A_BLOCKED.  
**Evidence:** Empty-DB migrations PASS; full backup/restore, second polling instance, reconnect and telemetry evidence not yet run.  
**Files changed:** None.  
**Regression:** Full current suite `116 passed`.  
**Decision:** Must run before beta; no claim based on tests only.  
**Blocker:** Gate sequencing and remaining operational evidence.

## TASK 8 — Live voice

**Status:** DEFERRED_GATE_A_BLOCKED.  
**Evidence:** Credential names/values are configured locally; no live audio was sent.  
**Files changed:** None.  
**Regression:** Existing voice tests remain green.  
**Decision:** No provider PASS without real synthetic RU/EN audio.  
**Blocker:** Gate sequencing and controlled voice test path.

## TASK 9 — Referral E2E

**Status:** DEFERRED_GATE_A_BLOCKED.  
**Evidence:** Single active `payment.py` route, helper-only `growth.py`, stable attribution/unit coverage.  
**Files changed:** Already captured in RC.  
**Regression:** Targeted growth tests `12 passed`.  
**Decision:** Must verify fresh-account `/start` and attribution live.  
**Blocker:** TASK 3 controlled account.

## TASK 10 — Live Stars/refund

**Status:** DEFERRED_P2.  
**Evidence:** Timed-pass copy corrected; no purchase/refund operation performed.  
**Files changed:** Locales already committed.  
**Regression:** Payment/product tests green.  
**Decision:** Do not change prices or payment stack.  
**Blocker:** Requires an allowed test payment path; does not block first controlled beta by itself.

## TASK 11 — Video drafts

**Status:** DEFERRED_P2.  
**Evidence:** Two video audit reports, multimodal analyses and growth playbook exist; no draft was published.  
**Files changed:** None in runtime.  
**Regression:** Not applicable.  
**Decision:** Prepare captioned/private-CTA/product-proof drafts only after live product proof; no automatic publishing.  
**Blocker:** TASK 3 product proof.

## TASK 12 — Invite-only beta 10–20 users

**Status:** NO-GO.  
**Evidence:** TASK 3 and TASK 4 are blocked; TASK 5/7/9 are not PASS.  
**Files changed:** None.  
**Regression:** Current full suite `116 passed` is insufficient for beta acceptance.  
**Decision:** Do not open a cohort or claim production readiness.  
**Blocker:** Explicit backlog prerequisites.

## Final decision

The RC is technically traceable and automated checks are green, but the execution cycle stops at the live gates. The next owner action is to provide a controlled Telegram test account and resolve the configured LLM provider response. After those are available, rerun TASK 3 and TASK 4 before opening any beta cohort.
