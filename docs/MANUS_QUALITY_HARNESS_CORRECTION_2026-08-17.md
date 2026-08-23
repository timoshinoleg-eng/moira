# Moira — quality harness correction — 2026-08-17

## Decision

> **The earlier 24-case provider results are not sufficient for a full semantic TASK 4 PASS.**

Sol’s independent audit correctly identified that `scripts/run_oracle_v6_eval.py::make_reading` invoked `interpret_reading` without `spread_id`. The shared function is also imported by the parallel 24-case runner. In the actual adapter, this parameter selects the Situation/Love/Choice rule and supplies the spread context used for position meanings. Thus, earlier completed 24-case runs prove provider transport, parsing, schema resilience and broad safety behavior, but do not prove the complete spread-specific Oracle prompt contract.

## Corrective implementation

| Change | Result |
|---|---|
| `make_reading` now calls `interpret_reading(..., spread_id=case["spread"])` | The sequential and parallel runners use the fixture spread type in the actual prompt path |
| New `tests/test_oracle_eval_spread_contract.py` | Confirms harness forwarding and asserts all RU/EN Situation/Love/Choice rule strings appear in the generated prompt |
| Prior public/private 24-case output files | Preserved under `*_PRE_SPREAD_FIX_2026-08-17.json` before the corrected run; no user data is involved because all fixtures are synthetic |
| Updated quality/beta reports | Earlier “provider-evidence PASS” wording is explicitly superseded, not silently overwritten |

## Corrected coverage run

A low-concurrency corrected-path sample covered **RU/EN × Situation/Love/Choice**. It completed with **5/6 LLM-structured** results, **1 safe deterministic fallback**, and **0 hard fails**. The five structured readings passed all recorded checks: card count/context, synthesis, practical focus, reflection, direct share-question check, natural length, mystical imagery and no-gibberish markers. The only fallback followed a malformed primary response and a short/invalid backup response.

This run establishes that the repaired harness reaches the full spread-specific prompt path and produces valid structured results under the current primary model. It is deliberately not promoted to a 24-case PASS because its size is six and the backup model remains broken.

## Regression and runtime

The full local suite passes **127 tests** after the correction; `compileall` for `bot` and `scripts` plus `git diff --check` pass. The active bot remains running with the current prompt/payment/privacy hardening already deployed. The harness change affects offline synthetic evaluation only and does not require a bot restart.

## Current quality gate

| Requirement | Status |
|---|---|
| Corrected runner includes spread-specific prompt contract | PASS |
| Corrected minimal RU/EN × 3-spread coverage | PASS — 5/6 structured, 0 hard fails |
| Corrected full 24-case blind provider run | OPEN |
| Functional tested backup model | OPEN — current liquid backup returns no usable completion |
| Owner blind rubric review | OPEN |
| TASK 4 acceptance | **OPEN** |
| TASK 12 beta decision | **NO-GO** |

## Next safe sequence

1. Select a free backup candidate that returns visible JSON-mode content, then perform a single synthetic smoke without exposing the key.
2. Run the corrected 24-case fixture at conservative concurrency after the backup is verified; preserve privacy-safe public metadata and owner-only synthetic review artifact.
3. Complete the owner blind rubric review of the corrected outputs.
4. Reconcile the beta gate only after those three facts exist; do not carry old runner outputs forward as full semantic quality evidence.
