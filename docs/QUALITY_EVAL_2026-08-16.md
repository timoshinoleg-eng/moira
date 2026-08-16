# Moira Quality Evaluation — 2026-08-16

## Status

**Status:** BLOCKED for the full LLM-vs-fallback acceptance gate; fallback fixture gate passes, while the live LLM provider smoke returned an empty response on two adapter attempts. No LLM score is invented.  
**Evaluation scope:** 24 unique synthetic cases, with no production questions or user-owned data.

## Coverage

| Dimension | Coverage |
|---|---:|
| Languages | RU 12 / EN 12 |
| Spreads | `situation`, `love`, `choice` |
| Question profiles per spread/language | decision, relationship, work, inner_change |
| Unique case IDs | 24 / 24 |
| Unique card triples | Generated from deck index with varying cases; no six-case cycle |
| Upright/reversed mix | Present across cases and positions |
| Card grounding | 24 / 24 structural checks |
| Synthesis field | 24 / 24 present |
| Reflection field | 24 / 24 present |
| Safety heuristic hard fails | 0 / 24 after rubric review |

The fixtures are stored in `tests/fixtures/quality_eval_24.json`. They contain only synthetic questions, deck IDs, orientations and evaluator flags.

## Fallback result

The fallback composer was executed with the same question, spread and drawn cards for every case. All 24 cases returned card-grounded output, synthesis and reflection. The evaluator found no deterministic mind-reading, medical/legal/financial instruction or missing reversed-orientation signal under the defined hard-fail patterns.

This is a **structural and safety smoke**, not a subjective quality score. The acceptance threshold `fallback >= 3.5/5` requires blinded human/owner rubric scoring of card grounding, question relevance, position relevance, reversed nuance, synthesis, natural language, actionable reflection, non-deterministic tone and repetition.

## Live LLM result

A one-case synthetic provider smoke was run against the current configured project path. The adapter made two attempts and returned an empty LLM response both times, then reported `LLM_RESULT_AVAILABLE=False`. The probe printed only status/field metadata and did not persist reading text. The current LLM quality comparison is therefore **BLOCKED**, not failed by a quality judgement and not passed by assumption.

Observed safe behavior:

```text
LLM_MODEL_CONFIGURED=True
LLM request failed (attempt 1): empty LLM response
LLM request failed (attempt 2): empty LLM response
LLM_RESULT_AVAILABLE=False
```

The live failure also emitted a non-blocking telemetry warning because the isolated smoke did not initialize the application database. This is a harness setup warning, not evidence of user-facing data loss.

## Decision

1. Keep deterministic fallback as the tested provider-failure path.
2. Do not claim an LLM score or complete the 24-case blinded comparison until the configured provider returns a non-empty structured response for the one-case smoke.
3. Once provider access is corrected, run both outputs with the same 24 fixtures, hide the mode labels, and conduct owner review. An independent judge is optional and must be labelled independent only if it is actually independent.
4. Do not add a second LLM, RAG stack or agent framework to solve this gate.

**TASK 4:** `IN_PROGRESS / BLOCKED_EXTERNAL_PROVIDER`.  
**Evidence:** 24-case fixture, fallback output checks, live one-case smoke output above.  
**Files changed:** `tests/fixtures/quality_eval_24.json`, this report.  
**Regression:** clean RC suite 115 passed; card/content subset 61 passed.  
**Blocker:** configured live LLM endpoint returned empty response twice; provider configuration/response requires owner or provider-side investigation.
Continuation 2026-08-16: provider /models probe timed out; no live LLM output or blinded 24-case quality score is asserted. TASK 4 remains BLOCKED.
Provider continuation 2026-08-16: OpenRouter free model openai/gpt-oss-20b:free returned a non-empty smoke response. This unblocks provider availability, but the 24-case blinded quality evaluation is still pending real execution.
Fallback continuation 2026-08-16: primary openai/gpt-oss-20b:free remains configured; backup nvidia/nemotron-3-super-120b-a12b:free returned a non-empty direct smoke response. OpenRouter documented models-array fallback is now sent through extra_body. Quality evaluation remains pending 24-case blinded execution.
Prompt quality continuation: v5-question-aware is implemented and schema regression is green. Full blinded 24-case live evaluation is not yet declared PASS; it requires live provider outputs and reliable bot/provider execution.
Current decision remains NOT PASS: the 24-case fixture and v5 prompt are ready, but repeated live provider/Telegram conditions are not stable enough for a truthful blinded quality verdict. No subjective score was invented.
Prompt continuation: PROMPT_VERSION v6-mystical-clear added a clear mystical voice contract: restrained imagery, natural modern language, card/position/question grounding, concrete action, open reflection, and explicit anti-gibberish rules against invented words, pseudo-esoteric jargon, abstraction chains, repetition, and beautiful filler. Targeted prompt/schema/fallback/voice tests 19 passed; full suite 116 passed; git diff --check clean. Live 24-case subjective quality score remains NOT DECLARED without stable provider evidence.
Oracle v6 evaluation continuation: prompt design and representative synthetic provider samples are CONDITIONAL PASS. 24-case fixture coverage remains valid, but full live-provider evaluation is BLOCKED pending a completed run without transient malformed/truncated provider outputs. See ORACLE_V6_EVALUATION_REPORT_2026-08-16.md.
