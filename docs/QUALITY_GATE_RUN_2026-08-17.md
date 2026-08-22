# Quality Gate Run — 2026-08-17 (night shift, ZCode)

**Scope:** full 24-case blinded fixture (`tests/fixtures/quality_eval_24.json`)
against the live configured provider path (OpenRouter, primary
`nvidia/nemotron-3-super-120b-a12b:free`, JSON mode on, backup
`liquid/lfm-2.5-2.6b:free`), prompt `v6-mystical-clear`, tag `v6-rc2`.

**Privacy:** only synthetic questions; no user data; key not disclosed.

## Provider config smoke

| Model | content | finish_reason | Verdict |
|---|---|---|---|
| `nvidia/nemotron-3-super-120b-a12b:free` (primary) | non-empty | stop | WORKING |
| `liquid/lfm-2.5-2.6b:free` (backup) | **empty** | **length** | **BROKEN — spends the whole budget on hidden reasoning and returns no visible content** |

Consequence: every adapter attempt-2 (backup) is currently doomed; the
effective reliability is primary-only. Recommendation: replace the backup with
`openai/gpt-oss-20b:free` (previously smoke-verified) or move the primary to a
paid route (`deepseek/deepseek-chat-*` class; ~$0.01–0.05 per 24-case run).

## Full runs (completed, not interrupted)

| Run | Structured | Fallback | Hard fails | Non-fatal check misses |
|---|---:|---:|---:|---|
| RUN1 (concurrency 3) | 22/24 (91.7%) | 2 (`ru-choice-work`, `en-situation-relationship`) | 0 | reflection_question 1, mystical_imagery 1 |
| RUN2 (concurrency 3) | 23/24 (95.8%) | 1 (`ru-love-decision`) | 0 | reflection_question 1, mystical_imagery 1 |

Artifacts: `docs/QUALITY_EVAL_V6_FULL_RESULTS.json` (RUN2 latest),
`docs/QUALITY_EVAL_V6_FULL_RESULTS_RUN2.json` (copy).

## Verdict

- Previous days' blocker (runs interrupted by sustained malformed/truncated
  free-provider output) is **resolved for the current primary**: two full runs
  completed back-to-back; on transient failures the adapter degraded to the
  safe deterministic fallback exactly as designed; zero hard-fail patterns
  (no deterministic predictions, no mind-reading, no medical/legal/financial
  instructions, no question echo in share summaries, no gibberish).
- Provider-evidence criterion of TASK 4: **PASS (two completed runs, 45/48
  structured, 0 hard fails)**. What remains for the full TASK 4 acceptance is
  the **owner blind rubric review** of LLM vs fallback (morning, human step —
  private JSONs prepared for it).
- Known residual risks: free-tier run-to-run variance (~4–8% fallback rate),
  broken backup model (must be replaced before beta), and no SLA on free
  OpenRouter routing. For the invite-only beta cohort this is acceptable with
  the deterministic fallback in place; for public launch a paid primary is
  recommended.

## Correction addendum — spread-contract harness audit (2026-08-17)

A subsequent independent audit found that both the sequential runner and the parallel runner called `interpret_reading(...)` without `spread_id`. Because `interpret_reading` passes `spread_id` into `_build_user_message`, the earlier 24-case runs did **not** select `SPREAD_RULES_RU` / `SPREAD_RULES_EN` or provide position-specific meaning for Situation/Love/Choice. Their 45/48 structured result remains useful **provider transport, schema and broad safety evidence**, but it is not sufficient semantic evidence for the complete spread-specific Oracle contract.

**Repair:** Shared `make_reading` now passes `spread_id=case["spread"]`. A regression test confirms the eval harness forwards this value and verifies that all RU/EN Situation/Love/Choice rules appear in the generated prompt for the corrected path. The parallel runner imports the shared helper and therefore receives the same correction.

**Corrected-harness coverage run:** A new low-concurrency synthetic RU/EN × Situation/Love/Choice run completed with **5/6 structured**, **1 deterministic fallback**, and **0 hard fails**. Every structured output passed the recorded schema, card count/context, synthesis, practical focus, reflection, direct share-question check, natural-length, mystical-imagery and no-gibberish checks. The fallback occurred after one malformed primary response and a backup validation failure; the configured backup remains a known blocker.

**Corrected verdict:** TASK 4 is **not yet PASS**. Current evidence is: (a) prior 24-case runs — transport/safety evidence only; (b) corrected-harness six-case spread-coverage run — promising but insufficient for the required 24-case blind semantic evaluation; (c) working backup replacement and a completed corrected 24-case run, followed by owner blind rubric review, remain required. The earlier statement “provider-evidence criterion of TASK 4: PASS” is superseded by this addendum.

## Immutable corrected 24-case attempt — provider reliability outcome (2026-08-17)

A new immutable baseline was created before a corrected full 24-case run: `docs/IMMUTABLE_QUALITY_EVAL_BASELINE_2026-08-17.json` (SHA-256 `bd9a11004dc9dea3a2db7a6d89c5876162ce754cd341864edc9c5e378bac4d2e`). It records current commit/worktree, fixture and harness hashes, spread-id forwarding, non-secret provider configuration and concurrency one.

The corrected full run was started with the spread-aware shared harness and `EVAL_CONCURRENCY=1`, but it was stopped after sustained empty/malformed/truncated JSON and schema-invalid provider responses. The runner completed no 24-case output file because it writes results only at completion; existing corrected six-case coverage and prior artifacts were preserved separately. The bot process was unaffected.

**Decision:** This is **BLOCKED_PROVIDER_RELIABILITY**, not a quality failure and not an incomplete PASS. TASK 4 remains OPEN. A tested working backup candidate, a new configuration-specific immutable baseline, a completed corrected 24-case artifact and owner blind rubric review are still required. See `docs/IMMUTABLE_QUALITY_RUN_REPORT_2026-08-17.md`.

## P0-1/P0-2/P0-3 implementation update (2026-08-17)

The backup is now `openai/gpt-oss-20b:free`, after one bounded synthetic JSON-mode smoke and one complete synthetic Oracle-schema smoke returned non-empty structured output with three card interpretations and a share summary. This is limited backup capability evidence, not a guarantee that free-tier batch output is reliable.

P0-2 is implemented and regression-tested: English card blocks use `upright` / `reversed` only; scorer flattening recursively scans the supplied user-visible reading payload (including nested `card_interpretations`) but not fixture question, seeded memory or run metadata. P0-3 is also implemented as a separate 16-case synthetic provider suite; its final reassessment records 15 structured results, one explicit deterministic fallback, zero failed-to-complete cases, 16/16 contract pass, and zero disclosure/language/canary/draw-contract failures. The fallback remains separately counted and is not represented as provider-structured success.

A version-2 immutable 24-case baseline is now recorded at `docs/IMMUTABLE_QUALITY_EVAL_BASELINE_2026-08-17.json`, SHA-256 `00e9922f4ba50261ad9733e91f112526482c2950c31fd03a81f54c6daf4de127`. A corrected serial 24-case attempt began from the preceding equivalent P0 baseline, but sustained malformed/truncated/short-field free-provider output prevented completion; the process was stopped and produced no final 24-case artifact. **TASK 4 remains OPEN and TASK 12 remains NO-GO.** Full privacy-safe evidence: `docs/MANUS_P0_1_P0_2_P0_3_EVIDENCE_2026-08-17.md`.
