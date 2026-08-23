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
Continuation 2026-08-16: TASK 0-2 recheck PASS at RC fcd0da74020eb0dc3df7e3d4e70c70d5d0a6fda1 with 116 passed and git diff --check clean. TASK 3 remains BLOCKED: no controlled Telegram test account. TASK 4 remains BLOCKED: configured deepseek-v4-flash at opencode.ai/zen/go/v1 returned no completed /models probe within bounded timeout; no live LLM score is claimed. Gate A remains NO-GO; no beta/public launch.
Provider continuation 2026-08-16: owner-supplied OpenRouter key verified locally without disclosure; LLM_BASE_URL=https://openrouter.ai/api/v1; LLM_MODEL=openai/gpt-oss-20b:free; provider smoke PASS with non-empty response; polling continuity PASS; getMe PASS; regression 116 passed. No beta/public launch performed.
Fallback continuation 2026-08-16: local test log review found 43 Telegram updates handled; the log contained 6 warning/error entries and did not provide privacy-safe step-level evidence for every requested UX action. No user questions or identifiers were copied into reports. Added LLM_BACKUP_MODEL=nvidia/nemotron-3-super-120b-a12b:free and OpenRouter extra_body models-array primary-first routing. Backup direct smoke PASS; primary+models syntax PASS; compile PASS; diff-check PASS; regression 116 passed; polling restarted and getMe PASS.
Continuation: prompt v5-question-aware added RU/EN question-intent, card-position-orientation grounding, reversed-card nuance, synthesis, concrete action, open reflection, and anti-gibberish/safety guardrails. Renderer adds a thin gold card frame while preserving original 78 card assets and provenance. Startup now treats command registration and webhook cleanup as non-blocking on transient Telegram API errors. Compile PASS; targeted LLM/fallback tests 22 passed; visual/render tests 2 passed.
Telegram availability continuation: user reported no bot response. Diagnosis found no running old instance, stale lock was cleared, and Telegram Bot API getMe returned HTTP 502 Bad Gateway. Startup reached Start polling but aiogram stopped on the same Telegram server error. Added TelegramAPIError retry loop with 10-second backoff; process now remains alive and logs repeated Start polling/retry markers instead of exiting. User-facing bot response remains BLOCKED by external Telegram API 502 until the service recovers.
Continuation: fresh isolated venv install completed and pytest returned 116 passed. Initial temp path used a redirected/non-ASCII Windows Temp location and Alembic path handling was inconclusive; alternative ASCII path C:\moira_audit\fresh_gate.db completed Alembic upgrade through 0005 and alembic check with no new operations. Restore copy verification also passed. Targeted growth/payment/voice/product tests 26 passed and standalone smoke passed.
Gate continuation: when checked, getMe/getUpdates succeeded once, but subsequent checks again returned HTTP 502 and polling entered bounded retry. Local TASK 7 restore, TASK 8 contract/error-path tests, TASK 9 growth tests, TASK 11 video drafts, and TASK 6 owner checklist progressed without external confirmation. Live Telegram, live STT, mobile devices, Stars/refund, and beta cohort remain unverified.
Oracle prompt continuation: repaired and finalized PROMPT_VERSION v6-mystical-clear. Added MYSTICAL_VOICE contract to system prompt while preserving schema v4, OpenRouter fallback routing, and deterministic fallback API. Prompt-related targeted tests 19 passed, full suite 116 passed, compile and diff-check PASS.
Visual continuation: reviewed representative 1080x1500 RU spread, 1080x1080 RU share, and 1080x1350 reversed single-card output. Added source-preserving card matte/inset/orientation frame treatment and corrected spread vertical balance. Visual targeted tests and full regression passed; mobile Telegram checks remain separately blocked.
Oracle v6 continuation: fixed explicit OpenRouter key precedence over legacy key file; switched to a verified content-capable free primary and free backup; added opt-in primary JSON mode; inserted card-born restrained mystical imagery and language-purity rules in the real reading prompt; ran synthetic provider checks. Representative run and repair retest passed without hard-fail patterns. Full 24-case concurrent provider run remains BLOCKED by malformed/truncated free-provider responses; not counted as PASS.

## Continuation — final restart and quality recheck (2026-08-16)

**Runtime recovery:** The prior `.bot.lock` was confirmed to be held by a non-existent PID and could not be released after process termination. The runtime guard was moved to `.bot.runtime.lock`; the lock helper now closes its local handle after failed acquisition. After a compile check, a single `bot.main` process was started as PID `24620`; it remained alive and owns the new runtime lock. The deployed configuration reports prompt `v6-mystical-clear`, the configured free primary and backup models, JSON mode enabled, and an OpenRouter key present without exposing it.

**Regression:** Full suite after the recovery patch: **119 passed** in 11.06 seconds.

**Questionnaire recheck:** The sequential `EVAL_LIMIT=1` synthetic run completed with exit code 0. The base RU scenario was `llm_structured`; both RU and EN question-lens checks were `llm_structured`, with mystical imagery, no gibberish markers, and card grounding all recorded as true. The evidence file remains privacy-safe and contains no real user question or reading.

**Full 24-case evaluation:** A new full blind run was attempted at `EVAL_CONCURRENCY=2`. It repeatedly encountered malformed, empty, truncated, and schema-overlength provider output despite retry/fallback handling. The run was intentionally stopped after sustained retries rather than generate additional free-tier load or claim a partial pass. Therefore TASK 4 remains **BLOCKED_EXTERNAL_PROVIDER** for the full provider-evidence acceptance criterion; representative questionnaire evidence is not substituted for it.

**Gate decision:** TASK 3 remains pending the owner's controlled Telegram E2E confirmation. TASK 12 remains **NO-GO**; no content publication or beta cohort was started.

## Continuation — provider-schema resilience repair (2026-08-16)

**Finding:** The attempted low-concurrency 24-case provider run surfaced a concrete recoverable validation failure: `card_interpretations[].context_connection` exceeded its declared 200-character limit. The parser previously clipped only `core_message`, so otherwise usable provider output could be rejected before the fallback path.

**Repair:** `parse_reading_json` now clips `core_message` (420), `symbolic_detail` (200), and `context_connection` (200) at word boundaries before Pydantic validation. This does not relax privacy, safety, required fields, or semantic validation; it aligns provider-normalization behavior with the existing schema. The regression test now covers both newly normalized card fields.

**Verification:** Targeted LLM schema/voice/config tests: **18 passed**. Full regression after the repair: **119 passed** in 11.74 seconds; `git diff --check` clean. The bot was restarted once to apply the repair and is polling as a single process (PID `14176`) with fresh `Start polling` / `Run polling` markers.

**Live E2E continuation:** Owner confirmed minimal post-restart replies to both one RU and one EN message. These are correctly recorded as two minimal core-response PASSes only; UI actions and referral remain unverified. The full 24-case quality gate remains blocked by repeated malformed/empty/truncated free-provider responses; this parser repair removes one known avoidable rejection but does not convert the incomplete run into PASS.

## Continuation — global visual overhaul (2026-08-17)

**Status:** VISUAL PASS WITH NON-BLOCKING REFINEMENT NOTES.

**Evidence:** Competitor and user-expectation research was saved to `docs/COMPETITOR_VISUAL_RESEARCH_2026-08-17.md`. The Nocturnal Thread art direction and autonomous production backlog were saved to `docs/MOIRA_VISUAL_ART_DIRECTION_2026-08-17.md`. A generated visual pack was created under `assets/generated_visuals/2026-08-17/`, including portrait altar and square share plates, a clean sigil, a deterministic vector thread overlay, and one private 8-second portrait video draft.

**Files changed:** `bot/visual/render.py`, `bot/visual/tokens.py`, visual QA notes, art direction and visual release package documents, generated visual assets, and refreshed visual smoke outputs. The source card illustration collection was not replaced or edited.

**Regression:** Full pytest suite `119 passed`; `compileall` passed; `git diff --check` passed; visual smoke generated RU/EN spread, share, and single-card outputs. Video draft integrity: H.264/AAC, 720x1280, 8 seconds. The first AI-generated transparent overlays were rejected after visual inspection because of green chroma contamination; the sigil was cleaned deterministically and the thread was recreated as a clean vector overlay.

**Decision:** Renderer-layer visual upgrade is locally ready for human review. No publishing, GitHub push, paid campaign, or beta launch was performed. TASK 12 remains governed by its existing Gate A and provider-quality blockers.

## Continuation — independent production-readiness review (2026-08-17)

**Status:** LOCAL RC HARDENING PASS; BETA NO-GO RETAINED.

**Current-code findings and repairs:** Review against the local worktree confirmed that public share output uses `Reading.share_summary` and a template caption, not raw interpretation; current rows have a direct question-leak guard and old rows use a generic summary. The remaining direct recent-reading-memory leak path was further hardened: share-summary prompt instructions now prohibit both question and recent-reading context, and validation rejects verbatim leakage of either source. The reading system message no longer says to follow user instructions exactly; it now treats question, card data, labels and memory as untrusted interpretation data and preserves system JSON/safety rules. A payment bug was confirmed: refunding one stacked unlimited-duration purchase set `unlimited_until=None` and erased all remaining time. The handler now removes only the refunded duration.

**Regression:** New focused regressions cover trust-boundary contract, exact recent-memory share leakage, and stacked 7/30-day refund arithmetic. Targeted suite: `24 passed`; existing payment idempotency script passed. Full suite after all current changes: **125 passed** in 11.84 seconds; compile checks and `git diff --check` passed.

**Runtime/reliability evidence:** The bot was restarted once to apply validated code as PID `23732`; process and `.bot.runtime.lock` were present and polling startup markers were observed. A separate verifier confirmed that a second process cannot acquire the live lock and releases its local failed-acquisition handle. A fresh online SQLite backup was made using retention `9999` (no retention deletion); an isolated integrity/table-presence verifier returned `BACKUP_SNAPSHOT_INTEGRITY_OK`.

**Gate reconciliation:** `docs/QUALITY_GATE_RUN_2026-08-17.md` supersedes only the old provider-execution blocker: two complete synthetic 24-case runs produced 45/48 structured outputs and zero hard-fail patterns. TASK 4 still needs owner blind-rubric review and a working backup-model smoke before it is considered fully accepted. TASK 3 has minimal RU reply PASS, EN reply PASS and owner-confirmed «Мои расклады» opening, but favorite/follow-up/share/delete/referral/mobile remain unverified. TASK 12 remains **NO-GO**; no public content, deployment, payment or beta cohort was started.

**Report:** `docs/MANUS_3H_PRODUCTION_READINESS_REPORT_2026-08-17.md` contains the full evidence table, fixed findings, residual risks and next actions.

## Correction — quality-evaluation spread-contract harness (2026-08-17)

**Finding:** Independent Sol audit reproduced a material harness omission: `scripts/run_oracle_v6_eval.py::make_reading` and, through it, the parallel runner called `interpret_reading` without `spread_id`. Earlier complete 24-case runs therefore bypassed `SPREAD_RULES_RU/EN` and spread-specific position-meaning context. Their outputs remain valid provider transport/schema/broad-safety evidence but are not complete semantic evidence for Situation/Love/Choice.

**Repair:** The shared helper now passes `spread_id=case["spread"]`; new `tests/test_oracle_eval_spread_contract.py` asserts both forwarding and actual inclusion of all RU/EN spread rules in generated prompt messages. Original output artifacts were preserved with `PRE_SPREAD_FIX_2026-08-17` names before the repaired run overwrote current-output filenames.

**Verification:** Corrected low-concurrency synthetic RU/EN × Situation/Love/Choice coverage completed **5/6 structured**, **1 safe deterministic fallback**, **0 hard fails**; all structured records passed the public metadata checks. Full regression after correction: **127 passed**; `compileall bot scripts` and `git diff --check` passed.

**Decision:** The prior provider-execution PASS wording is retracted. TASK 4 is **OPEN** until a corrected full 24-case run, a working tested backup model and the owner blind rubric review are complete. TASK 12 remains **NO-GO**. Full details: `docs/MANUS_QUALITY_HARNESS_CORRECTION_2026-08-17.md`.

## Continuation — corrected immutable 24-case provider attempt (2026-08-17)

**Status:** BLOCKED_PROVIDER_RELIABILITY; TASK 4 remains OPEN and TASK 12 remains NO-GO.

**Evidence:** The immutable baseline `docs/IMMUTABLE_QUALITY_EVAL_BASELINE_2026-08-17.json` was created before execution (SHA-256 `bd9a11004dc9dea3a2db7a6d89c5876162ce754cd341864edc9c5e378bac4d2e`; commit `d0f442bb42520b3389b3df4475a87ed93de8a6cc`; full synthetic fixture and harness/config hashes recorded). The corrected spread-aware full fixture was started at serial concurrency. It was stopped after sustained empty, malformed and truncated JSON plus schema-invalid short card fields from the free provider. No partial 24-case final artifact was produced or treated as a PASS; the pre-existing corrected six-case metadata remains 5/6 structured, 1 safe fallback and 0 hard fails.

**Files changed:** `docs/IMMUTABLE_QUALITY_RUN_REPORT_2026-08-17.md`, `docs/QUALITY_GATE_RUN_2026-08-17.md`, `docs/BETA_READINESS_REPORT_2026-08-16.md`, and this execution log. The existing public/private coverage artifacts were preserved with `PRE_IMMUTABLE_2026-08-17` names before the attempt.

**Regression/runtime:** No source code changed in this run. The separate bot process PID `23732` remained alive after stopping the evaluation process.

**Decision/blocker:** Do not weaken the schema, declare an incomplete run successful, publish content or open beta. Replace and smoke-test the free backup candidate; generate a new configuration-specific immutable baseline; obtain a completed corrected 24-case artifact; then obtain the owner blind rubric. The privacy-safe baseline, outcome report and updated gate reports were uploaded to Workspace folder 06.

## Continuation — P0-1/P0-2/P0-3 hardening and provider evidence (2026-08-17)

**Status:** P0-1 PASS (bounded backup smoke); P0-2 PASS (deterministic regressions); P0-3 PASS (separate provider-executed contract); P0-4 remains BLOCKED_PROVIDER_RELIABILITY. TASK 4 remains OPEN and TASK 12 remains NO-GO.

**P0-1:** The broken liquid backup was replaced in `.env` with `openai/gpt-oss-20b:free`. Current catalog/one-request checks found stale Mistral unavailable and a named Gemma candidate denied, while GPT-OSS passed synthetic JSON-mode and a complete `interpret_reading` Oracle-schema smoke (three structured card interpretations and share summary) using an isolated smoke database. This does not overstate free-tier batch reliability.

**P0-2:** Fixed `_build_card_block()` so the EN orientation is always `upright` or `reversed`, never a Russian token. Replaced top-level-only scorer flattening with recursive traversal of the passed user-visible reading payload. New regressions prove nested markers are detected while matching strings solely in synthetic question or run metadata are ignored.

**P0-3:** Added the exact 16-case Sol fixture, isolated DB/provider runner, deterministic contract tests and public/private evidence split. Provider execution completed 15 structured outputs, one explicit deterministic fallback and no failed completions. The initial evaluator incorrectly demanded card names in fallback card text even though the product photo caption renders those names from the same draw; a new Q02 regression corrected the check to the actual fallback fields (position label, position meaning and orientation). Preserved outputs were reassessed without new provider calls: 16/16 contract pass; zero prompt/system disclosure, language, canary or draw-contract failures. The fallback remains counted separately.

**Regression:** Full suite after all P0 work: **146 passed**; `compileall bot scripts` and `git diff --check` passed. Bot PID `23732` remained alive.

**Immutable quality gate:** Created version-2 baseline `docs/IMMUTABLE_QUALITY_EVAL_BASELINE_2026-08-17.json`, SHA-256 `00e9922f4ba50261ad9733e91f112526482c2950c31fd03a81f54c6daf4de127`. A corrected serial 24-case run began from the preceding equivalent P0 baseline but was stopped after sustained malformed/truncated/schema-invalid free-provider output. It created no completed final artifact; prior outputs were preserved. Do not begin owner blind rubric or beta. Full report: `docs/MANUS_P0_1_P0_2_P0_3_EVIDENCE_2026-08-17.md`.
