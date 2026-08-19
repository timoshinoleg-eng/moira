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
Additional local evidence: fresh venv pytest 116 passed; ASCII-path fresh DB Alembic upgrade through 0005 and alembic check PASS; targeted growth/payment/voice/product suite 26 passed; standalone smoke PASS. Mobile QA checklist and video creative drafts prepared without publishing.

## Continuation — minimal live response (2026-08-16)

An owner-controlled Telegram test confirmed that `@MoiraOraclebot` replied to one live Russian message after the final restart. At the same time, the runtime showed exactly one `bot.main` process and the polling log was freshly written. No user message, reading text, identifier, username, screenshot, or referral data was collected.

| Check | Result | Evidence |
|---|---|---|
| RU message → bot reply | PASS (minimal core response only) | Owner confirmation plus a live single-process polling runtime; content intentionally not retained. |
| EN message → bot reply | NOT VERIFIED | No owner confirmation for an English message. |
| Result controls: history/reopen, favorite, follow-up, share, delete | NOT VERIFIED | The user confirmed a reply only; the remaining interface actions were not claimed. |
| Referral deep link and attribution | NOT VERIFIED | Requires an isolated new-account test flow. |

**Decision:** This is valuable partial evidence, but does not close TASK 3. The broader controlled E2E chain remains open and TASK 12 remains NO-GO.

**RU/EN response continuation:** The owner then confirmed that the same live bot also replied to a minimal English test message. The evidence therefore supports **RU message → reply PASS (minimal)** and **EN message → reply PASS (minimal)**. It does not establish language quality beyond delivery, nor verify any result control, history, favorite, follow-up, share, delete, referral, mobile, voice, or payment flow. No message or reading content was retained.

## UI label correction from owner screenshot (2026-08-16)

The owner-provided privacy-safe screenshot shows that the Russian main-menu label exposed to the user is **«Мои расклады»**, not «История». This is the user-facing entry point for saved readings and should be used in the E2E checklist. The same screenshot visibly shows result actions for **sharing**, **removing from favorites**, **positive/negative feedback**, two follow-up actions, and **Menu**. The screenshot itself is not copied into the evidence report and no reading text or personal identifier is retained.
