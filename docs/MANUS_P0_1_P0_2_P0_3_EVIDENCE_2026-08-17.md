# Moira — P0-1, P0-2 and P0-3 implementation evidence — 2026-08-17

## Decision

> **P0-1 backup smoke: PASS. P0-2 deterministic regressions: PASS. P0-3 provider-executed synthetic contract: PASS after a transparent deterministic reassessment of one fallback check. P0-4 corrected immutable 24-case semantic run: BLOCKED_PROVIDER_RELIABILITY. TASK 4 remains OPEN and TASK 12 remains NO-GO.**

This record separates completed Manus-owned current-worktree changes from the outstanding corrected 24-case quality artifact. It contains only synthetic case identifiers, non-secret fingerprints and aggregate checks; it contains no user question, reading, identifier, provider key or raw owner-review output.

## P0 status matrix

| Priority | Status | Evidence | Scope boundary |
|---|---|---|---|
| P0-1 — working free backup | PASS (bounded smoke) | `openai/gpt-oss-20b:free` returned valid JSON in one synthetic JSON-mode request and one full synthetic Oracle reading: structured result, 3 card interpretations, share summary present | This proves the named backup can answer the bounded smoke; it does not promise batch reliability of free providers. |
| P0-2 — EN orientation | PASS | `_build_card_block()` now branches on language before orientation selection; 5 orientation regressions cover RU/EN upright/reversed and mixed EN blocks | EN no longer receives the Russian reversed-orientation token. |
| P0-2 — recursive scorer | PASS | `flatten()` now recursively traverses only the passed reading payload; 5 regressions cover nested hard-fail/gibberish detection and exclude question/run metadata | The scorer is intentionally not given fixture question, seeded memory or run metadata. |
| P0-3 — 16 synthetic provider cases | PASS (contract) | 15 structured outputs, 1 documented deterministic fallback, 0 failed-to-complete; final reassessment: 16/16 contract pass, 0 disclosure/language/canary/draw-contract failure | This suite is deliberately separate from the ordinary 24-case quality denominator. |
| P0-4 — corrected immutable 24-case quality artifact | BLOCKED_PROVIDER_RELIABILITY | New baseline created; serial run started, then stopped after sustained malformed/truncated/schema-invalid free-provider outputs; no completed final artifact | No partial run is accepted as semantic PASS. |
| Owner blind rubric | OPEN | Sol rubric is prepared in Workspace | Must be completed only after a completed corrected 24-case artifact exists. |

## P0-2 implementation and deterministic verification

The language/orientation bug was independently reproduced in the current adapter and fixed with an explicit RU/EN branch. The evaluation scorer previously flattened only top-level strings, so hard-fail and gibberish markers nested under `card_interpretations` escaped automated detection. It now recurses through the **user-visible reading payload only**. This preserves the Sol boundary: malicious input text in a fixture question, continuity memory or run metadata cannot manufacture a false output hard fail.

The new `tests/test_sol_oracle_gate_regressions.py` covers four localized orientation cases, a mixed English block, nested hard-fail detection, nested gibberish detection, question-only marker exclusion, metadata-only marker exclusion and a clean nested reading. The broader P0 test set also checks fixed `spread_id` propagation and the existing LLM trust boundary.

## P0-3 synthetic provider evidence

The implementation adds a separate fixture, runner and deterministic contract tests:

| Artifact | Purpose |
|---|---|
| `tests/fixtures/oracle_p0_3_adversarial_16.json` | The exact 16 Sol case IDs: Q01–Q08, M01–M05, C01, P01 and P02. All values are synthetic. |
| `scripts/run_oracle_p0_3_adversarial_eval.py` | Serial real `interpret_reading` provider path, real `spread_id`, isolated temporary SQLite memory store, public/private result separation and artifact SHA-256. |
| `tests/test_oracle_p0_3_adversarial_contract.py` | Fixture, card-data isolation, language, disclosure, canary, memory-conflict and fallback-presentation deterministic regressions. |
| `docs/ORACLE_P0_3_ADVERSARIAL_PUBLIC_RESULTS.json` | Original provider-executed public metadata artifact. |
| `docs/ORACLE_P0_3_ADVERSARIAL_REASSESSMENT_PUBLIC_RESULTS.json` | Final deterministic reassessment of the same preserved provider outputs. SHA-256 `64cf772b30f272fd3e1bd1425cd641268850293aa5e1e57347d9b05a5b63c450`. |

The original P0-3 public artifact recorded 15 structured outputs, one deterministic fallback and one contract failure. The only failing check was the fallback evaluator’s requirement that `compose_fallback_reading().card_texts` repeat a card name. This was an evaluator defect, not a provider disclosure, canary, language or draw error: the product’s spread photo/caption presents the names from the same `DrawnCard` collection, while the deterministic textual fallback itself renders position label, position meaning and orientation. The check was corrected to validate exactly those rendered fallback fields. A new deterministic regression reproduces Q02 and passes. The preserved provider outputs were then reassessed without issuing any new model requests; all 16 cases passed the agreed contract.

The final reassessment records: **15 structured; 1 documented deterministic fallback; 0 failed-to-complete; 16/16 contract pass; 0 prompt/system disclosure; 0 wrong-language escape; 0 share canary leak; 0 accepted draw-identity failure.** The fallback remains explicitly counted and is not reclassified as provider-structured success.

## Backup candidate evidence

The stale candidate `mistralai/mistral-7b-instruct:free` was not available from the current provider catalog, and the named Gemma candidate was denied at request time. A live catalog probe was used only to enumerate accessible `:free` model identifiers without printing credentials. `openai/gpt-oss-20b:free` then passed a bounded synthetic JSON-mode smoke and a full synthetic English Oracle reading through `interpret_reading` with three schema-valid card interpretations and a share summary. Runtime configuration now names that model as `LLM_BACKUP_MODEL`.

## Regression and immutable-run status

The final local verification returned **146 passed**, `compileall` passed, and `git diff --check` passed. A new version-2 immutable baseline was created after the final P0-3 evaluator correction:

| Baseline field | Value |
|---|---|
| Path | `docs/IMMUTABLE_QUALITY_EVAL_BASELINE_2026-08-17.json` |
| SHA-256 | `00e9922f4ba50261ad9733e91f112526482c2950c31fd03a81f54c6daf4de127` |
| Run ID | `immutable-corrected-24case-p0-2-p0-3-2026-08-17` |
| Commit SHA | `d0f442bb42520b3389b3df4475a87ed93de8a6cc` |
| Configuration | primary `nvidia/nemotron-3-super-120b-a12b:free`; backup `openai/gpt-oss-20b:free`; JSON mode; concurrency one; no secret recorded |

A serial corrected 24-case run was started from the preceding, otherwise equivalent P0 baseline and prior result files were preserved. It produced sustained empty/malformed/truncated JSON and schema-invalid short card fields. It was stopped before completion to avoid unbounded free-tier churn. The runner writes its full artifacts only after all cases complete, so it created no false partial 24-case result; the prior corrected six-case coverage remains unchanged at 5/6 structured, one safe fallback and zero hard fails. The current version-2 baseline is ready for the next complete 24-case attempt, but no completed artifact exists under it.

## Gate implication

The P0-1/P0-2/P0-3 work removes the confirmed backup, localization, scorer-scope, continuity-memory and adversarial-suite gaps. It does **not** close the governing quality gate. Before any owner blind rubric or beta decision, the team still needs a completed corrected immutable 24-case output under the current baseline. The bot process remains alive; no publication, cohort launch, GitHub push, payment action or real-user-data test was performed.
