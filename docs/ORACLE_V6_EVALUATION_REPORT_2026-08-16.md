# Oracle v6 — Synthetic Quality Evaluation

**Date:** 2026-08-16
**Scope:** Prompt v6, OpenRouter routing, structured-output reliability, and synthetic RU/EN tarot readings.
**Privacy:** All provider inputs used only synthetic questions and synthetic card combinations. This report contains no real user questions, identifiers, tokens, or raw readings.

## 1. Scope of visual updates

The **78 source card illustrations were not regenerated or replaced**. The update applies to the renderer layer used by every card: dark altar matte, inset, upright gold frame, reversed rose frame, glow, and spread composition balance. Provenance of the source deck is unchanged.

## 2. Evaluation method

The evaluation fixture contains 24 unique synthetic cases across two languages, three spreads, and four question profiles. The live evaluation additionally used paired, same-card question-lens probes to test whether the answer changes when the synthetic question changes.

The automated checks require a three-card result, nonempty card/core/context fields, synthesis, practical focus, reflection question, safe share summary, meaningful overall length, no configured gibberish markers, and no configured deterministic/mind-reading hard-fail patterns. A manual quality review then evaluates clarity, card grounding, language purity, and restrained mystical imagery.

## 3. Defects found and repaired

| Finding | Repair | Evidence |
|---|---|---|
| New OpenRouter key was masked by legacy `LLM_API_KEY_FILE` | Explicit `OPENROUTER_API_KEY` now takes priority; legacy file remains fallback only | Config regression covers both branches; provider authentication restored |
| Primary free model could expose reasoning without visible content | Routing changed to a content-capable NVIDIA free primary and explicit NVIDIA free backup | Direct smoke confirms visible content for both configured models |
| Plain JSON responses could be malformed or truncated | JSON mode is opt-in and enabled only for the verified primary; backup receives strict plain-JSON prompt without incompatible parameters | Primary JSON-mode smoke returned valid JSON |
| Schema encouraged verbose padding and rejected concise natural sentences | Minimum field lengths were reduced while upper bounds and required fields remain; prompt length guidance now matches schema | Structured RU/EN results accepted without artificial expansion |
| Main reading path lacked the new mystical voice contract | Card-born mystical image and language-purity proofread are now part of `VOICE_RU`/`VOICE_EN` and the real prompt path | Targeted prompt-contract tests pass |
| Some readings were clear but too coaching-like | Prompt now requires exactly one restrained symbol-derived image with explanation in opening or synthesis | Repaired RU/EN retest has 100% mystical-imagery rule pass |

## 4. Live synthetic evidence

| Evaluation | Result | Decision |
|---|---:|---|
| Bounded RU base case + RU/EN same-card question-lens probes | 3/3 structured, no hard fail; question-lens output hashes differed | PASS |
| Representative 8-case RU/EN run across all spreads and profiles | 7/8 structured initially; 0 hard fails; 2 imagery misses | Repair required |
| Post-repair retest of former weak cases plus EN control | 3/3 structured; all automatic checks passed | PASS |
| Former fallback RU choice case after concise-core adjustment | 1/1 structured; all checks passed | PASS |
| Full 24-case concurrent provider attempt | Interrupted after repeated malformed/truncated free-provider responses; no completed artifact | BLOCKED — do not count as PASS |

## 5. Quality verdict

The prompt now produces clear, card-grounded, restrainedly mystical readings in the confirmed synthetic samples. It avoids configured gibberish, deterministic future claims, mind-reading claims, raw-question leakage into share copy, and unsupported factual assertions. The current model routing is more reliable than the prior configuration because it uses the active OpenRouter key, verified JSON mode for the primary, and an explicit free backup.

**Quality status: CONDITIONAL PASS for prompt design and representative live samples.** The final 24-case provider-wide quality gate remains **BLOCKED**, not PASS, until a full run completes without the observed transient malformed/truncated free-provider responses.

## 6. Regression evidence

The following test areas were updated or exercised: prompt voice contract, key precedence, fallback behavior, fixture coverage, adapter/config compile checks, and the full project test suite. Results are recorded in the execution log after the final test run.

## 7. Final regression result

After the repair set, the full local project suite completed with **119 passed**. Python compile checks and `git diff --check` also passed. The inventory increased from the earlier 116-test reference because the work added a second key-precedence regression branch and two Oracle voice-contract checks; no existing test coverage was removed.
