# Moira — corrected immutable 24-case quality-run outcome — 2026-08-17

## Result

> **Outcome: BLOCKED_PROVIDER_RELIABILITY. No completed immutable 24-case result was produced. TASK 4 remains OPEN and TASK 12 remains NO-GO.**

The corrected spread-aware 24-case run was started after an immutable baseline was recorded. It used the shared `make_reading` path with `spread_id=case["spread"]`, the full 24-item synthetic fixture, JSON mode and `EVAL_CONCURRENCY=1`. The process was intentionally stopped after sustained malformed, truncated and schema-invalid free-provider responses, rather than allowing an unbounded sequential job to consume further quota and still fail to produce a complete artifact.

## Immutable baseline

| Field | Recorded value |
|---|---|
| Baseline artifact | `docs/IMMUTABLE_QUALITY_EVAL_BASELINE_2026-08-17.json` |
| Baseline SHA-256 | `bd9a11004dc9dea3a2db7a6d89c5876162ce754cd341864edc9c5e378bac4d2e` |
| Commit SHA | `d0f442bb42520b3389b3df4475a87ed93de8a6cc` |
| Branch | `feat/moira-production-readiness` |
| Fixture | 24 unique synthetic cases; SHA-256 recorded in baseline |
| Harness | spread-aware shared helper; sequential/parallel runner and adapter SHA-256 recorded in baseline |
| Provider configuration | primary `nvidia/nemotron-3-super-120b-a12b:free`; backup `liquid/lfm-2.5-2.6b:free`; JSON mode; non-secret fields only |
| Concurrency | 1 |

## Observed run behavior

The provider emitted repeated empty or malformed JSON (`Expecting value` / invalid property syntax), a truncated JSON shape, and short card-core messages below the declared 40-character minimum. These are provider-output failures, not a reason to weaken the reading schema or classify the run as passed. The current backup remains known to provide no usable visible completion under failure conditions.

Because the parallel runner writes its public and private result files only after all cases finish, the interrupted process did **not** create a false partial 24-case artifact. The earlier corrected six-case coverage public metadata remains unchanged at **5/6 structured, 1 safe fallback, 0 hard fails**. It was separately preserved before this run as `QUALITY_EVAL_V6_FULL_RESULTS_PRE_IMMUTABLE_2026-08-17.json`; the run also preserved the prior synthetic owner-only artifact.

## Integrity checks

| Check | Result |
|---|---|
| Immutable baseline generated before run | PASS |
| Existing corrected coverage output preserved | PASS |
| Interrupted run overwrote no final 24-case output | PASS |
| Active bot process | PASS — still alive; evaluation process was separate |
| Completed immutable 24-case provider artifact | FAIL — not produced |
| Functional fallback route | FAIL — current liquid backup remains unusable |

## Gate implication and next path

A 24-case semantic evaluation cannot be declared complete from a started-but-interrupted process. The existing corrected six-case sample remains useful only as limited spread-path coverage. Only a completed machine-readable artifact, followed by the owner blind rubric review, can advance TASK 4.

## P0 follow-up update — current baseline and provider evidence (2026-08-17)

P0-1 is no longer blocked by the liquid backup: `openai/gpt-oss-20b:free` passed bounded JSON-mode and full synthetic Oracle-schema smokes. P0-2 deterministic orientation/scorer regressions pass. P0-3 completed separately through the real provider path with 15 structured outputs, one explicit deterministic fallback and, after a tested reassessment of the fallback payload contract, 16/16 contract pass with no disclosure, language, canary or draw-identity failure. These results are not mixed into the ordinary 24-case quality denominator.

A current version-2 immutable baseline now supersedes the historical baseline table above for the next full quality attempt: SHA-256 `00e9922f4ba50261ad9733e91f112526482c2950c31fd03a81f54c6daf4de127`; primary `nvidia/nemotron-3-super-120b-a12b:free`; backup `openai/gpt-oss-20b:free`; JSON mode; concurrency one. A serial 24-case attempt under the preceding equivalent P0 baseline still encountered sustained malformed/truncated/schema-invalid free-provider output and was stopped without writing a final 24-case artifact. The next complete corrected 24-case run must use the current version-2 baseline; until it exists, TASK 4 remains OPEN.

No user question, reading, identifier, provider key, database record or raw private owner-review output is included in this report.
