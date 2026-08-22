# Moira — Manus 3-hour production-readiness report — 2026-08-17

**Scope:** Independent review of the current local worktree, synchronized with Sol’s situation review and autonomous brief. This report covers only evidence collected during the review. It does not authorize publication, payment, deployment to a VPS, GitHub push, or beta launch.

## Executive verdict

> **Verdict: stronger local RC, but invite-only beta remains NO-GO.**

The current worktree is materially more robust than the older beta report alone suggests. Provider execution evidence improved: two complete synthetic 24-case runs finished with 45/48 structured results and zero hard-fail patterns. The former sustained provider-run interruption is therefore resolved for the current primary model. However, the configured backup model is conclusively broken, the owner blind rubric review is still pending, and the controlled Telegram E2E chain is only partially complete. Those facts prohibit promotion to a beta PASS.

## Current verification results

| Area | Result | Evidence |
|---|---|---|
| Full regression | **PASS — 125 passed** | Current local `pytest -q` after the new refund, trust-boundary and share-privacy regressions |
| Targeted LLM/payment hardening | **PASS — 24 passed** | `test_llm_schema`, `test_llm_trust_boundary`, `test_payment_refund_regression`, config/voice tests; existing payment idempotency script also passed |
| Compile and diff hygiene | PASS | `compileall` for `bot`/`deploy`, `py_compile` for updated modules and `git diff --check` |
| Live runtime | PASS — one process, lock present, polling startup markers observed | Current-code restart, PID `23732`; no user content retained |
| Second instance guard | PASS | Separate verifier was rejected by `.bot.runtime.lock` and retained no local lock handle |
| Backup snapshot | PASS | New online SQLite backup made with retention `9999` (no backup deletion); isolated integrity/table check passed |
| Share privacy trace | PASS for direct/raw paths; residual paraphrase risk | Public image uses stored `share_summary`; public caption is template/referral link; legacy rows use generic summary; current prompt and guard reject direct question/recent-memory leakage |
| Stacked unlimited refund | **BUG FOUND AND FIXED** | Previous code erased all unlimited entitlement on any days-product refund; now subtracts only refunded duration, with three new regression tests |
| LLM trust boundary | **WEAKNESS FOUND AND FIXED** | Previous system text delegated instruction priority to user data; replaced by a system contract that treats question/card/memory content as untrusted interpretation data |

## Code changes made during this review

| File | Change | Validation |
|---|---|---|
| `bot/handlers/payment.py` | Added `_revoke_unlimited_days`; refunds of 7/30-day products no longer erase stacked time wholesale | New `tests/test_payment_refund_regression.py`; existing `test_patch2_payments.py` passed |
| `bot/llm/adapter.py` | Added `READING_SYSTEM_CONTRACT`; removed unsafe “Follow the user's instructions exactly” wording | New `tests/test_llm_trust_boundary.py` |
| `bot/llm/adapter.py` | Explicitly excludes question and recent-reading context from share summary; direct leakage guard now checks both sources | Extended `tests/test_llm_schema.py` |
| `tests/test_payment_refund_regression.py` | New pure regression coverage for stacked duration refunds | 3 pytest cases |
| `tests/test_llm_trust_boundary.py` | New system-contract regression coverage | 2 pytest cases |
| `docs/LIVE_GATE_REPORT_2026-08-16.md` | Added owner-confirmed «Мои расклады» open result after recovery | Privacy-safe evidence only |

## Findings from Sol reconciled against current code

| Sol finding | Current-code verdict | Resolution / residual action |
|---|---|---|
| Old GitHub main was an unsafe source of truth | CONFIRMED | All findings in this report come from current local worktree `d0f442b+`, not the old GitHub main |
| Provider backup `liquid/lfm-2.5-2.6b:free` is broken | CONFIRMED HIGH | It returns empty output with `finish_reason=length`; replace and smoke-test before beta |
| LLM trust boundary is weak | CONFIRMED HIGH, FIXED LOCALLY | System contract and regression now defend against instruction text inside untrusted reading data; adversarial provider test remains advisable |
| Share may expose private data | CONFIRMED SAFE for current direct/raw path; residual paraphrase risk | Generic fallback for old rows, prompt rule, direct leak guard, and no raw interpretation in public caption; human review remains needed |
| Refund semantics require current-code verification | CONFIRMED BUG, FIXED LOCALLY | Days-product refund previously removed all stacked unlimited time; fixed and regression-tested |
| Full provider run remains unproven | UPDATED | `QUALITY_GATE_RUN_2026-08-17.md` documents two completed runs, 45/48 structured and zero hard fails; blind owner review and backup replacement remain |

## Gate delta

| Gate | Earlier state | Current evidence-based state | What still blocks closure |
|---|---|---|---|
| TASK 3 — Telegram E2E | Blocked | **PARTIAL**: RU reply, EN reply, and «Мои расклады» entry are owner-confirmed | Favorite, bounded follow-up, share, delete, referral and mobile checks remain |
| TASK 4 — quality | Blocked external provider | **PROVIDER EXECUTION PASS / TASK ACCEPTANCE PENDING**: 2 complete 24-case runs, 45/48 structured, 0 hard fails | Owner blind rubric review; replace broken backup model and re-smoke it |
| TASK 7 — reliability | Deferred | **PARTIAL PASS**: live single-instance lock, online backup integrity, current process/polling and test evidence | Controlled reconnect/restore-to-stopped-instance evidence and operating checklist review |
| TASK 10 — payments | Deferred | **LOCAL HARDENING PASS**: idempotency test retained; stacked-unlimited refund bug fixed | Authorized live Stars/refund path remains separate and optional for initial beta |
| TASK 12 — beta | NO-GO | **NO-GO remains** | Full required E2E, quality blind review, working backup and gate reconciliation |

## Required next actions

1. Replace `LLM_BACKUP_MODEL=liquid/lfm-2.5-2.6b:free` with a verified content-producing free candidate, then execute one JSON-mode synthetic smoke before calling fallback reliable. This is a local configuration/deployment change and must not expose the key.
2. Owner performs the remaining controlled Telegram checklist using only PASS/FAIL labels: favorite, one bounded follow-up, share, delete, referral deep-link/attribution, and mobile rendering. No questions, readings, identifiers or referral codes are needed in evidence.
3. Owner completes the prepared blind rubric review over synthetic LLM/fallback outputs. The review can use the owner-controlled private synthetic documents but must not be exported publicly.
4. Manus runs an adversarial synthetic prompt test against the current system contract after the backup candidate is settled. The test should verify that instruction-like text in question/card/memory fields does not alter the output schema or safety rules.
5. Update `BETA_READINESS_REPORT_2026-08-16.md` via a dated addendum rather than rewriting historical evidence. It must show TASK 4’s provider-execution improvement, the blind-review requirement, current backup risk, and retained beta NO-GO.

## Safety and release boundary

No user questions, readings, identifiers, credentials, databases, referral codes, payment information or raw runtime logs were copied into this report. No beta cohort, public content, GitHub push, paid provider route, VPS deployment, or payment transaction was started. The active bot was only restarted once to apply the locally validated hardening changes.

## Reference artifacts

- `QUALITY_GATE_RUN_2026-08-17.md`
- `LIVE_GATE_REPORT_2026-08-16.md`
- `BETA_READINESS_REPORT_2026-08-16.md`
- `MANUS_EXECUTION_LOG_2026-08-16.md`
- `MANUS — Autonomous 3h Production Readiness Brief` in Google Workspace folder `06 — Sol Production Review & Manus 3h Plan`
