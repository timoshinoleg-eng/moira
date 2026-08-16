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
