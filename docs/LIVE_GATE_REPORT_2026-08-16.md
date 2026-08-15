# Moira Live Gate Report — 2026-08-16

## Status

**Status:** BLOCKED — controlled Telegram E2E is not completed.  
**Bot credential probe:** PASS for read-only identity check.  
**Public deployment:** not performed.  
**Evidence policy:** no personal test questions, usernames or reading text are included.

## Evidence obtained

| Check | Result | Evidence |
|---|---|---|
| Bot API credential / identity | PASS | Read-only `getMe`: HTTP 200; bot identity returned as `MoiraOraclebot` / `Таро Вопрос`. Token was not printed or stored in evidence. |
| Controlled test account | BLOCKED | No separate controlled Telegram user/account was available to perform the required interaction sequence. |
| RU core flow | NOT VERIFIED | Requires test account: start → spread → synthetic question → result → visual → history → reopen → favorite → follow-up → share → delete. |
| EN core flow | NOT VERIFIED | Same controlled account dependency. |
| Real LLM provider | BLOCKED_EXTERNAL_PROVIDER | One synthetic smoke made two adapter attempts and returned empty response; fallback path remained safe. |
| Provider failure → fallback | PASS locally / live Telegram NOT VERIFIED | Existing unit/integration tests and 24-case fallback evaluation pass; live delivery still needs controlled account. |
| iOS/Android delivery | BLOCKED | No real iOS/Android access was used; desktop preview is not promoted to PASS. |

## Required next action

Use a dedicated owner-controlled Telegram test account, separate from the production-like polling identity, and execute the synthetic RU and EN checklist. Save only privacy-safe screenshots/log excerpts labelled with a test account alias. Do not publish or start a beta cohort until the same reading chain is verified for result, history/reopen, favorite, bounded follow-up, share and delete.

**Decision:** TASK 3 remains `BLOCKED_EXTERNAL_ACCOUNT`; Gate A and TASK 12 beta remain blocked. No claim of live production readiness is made from this report.
