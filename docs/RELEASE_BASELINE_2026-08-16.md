# Moira Release Baseline — 2026-08-16

## Status

**Status:** PASS for baseline normalization; release candidate is not yet sealed.  
**Evidence date:** 2026-08-16.  
**Current HEAD:** `ea9dea0dd694bd934bc958d67fbb34482ef0641f`.

This report is based on the current local worktree, not on the historical `c13ae5d` checkout. Historical findings are treated as resolved only where current evidence reproduces the resolution.

## Current worktree

The worktree is intentionally dirty before TASK 1. The following files are release-relevant changes already present or added during the growth cycle:

```text
.env.example
bot/config.py
bot/handlers/reading.py
bot/handlers/payment.py
bot/handlers/growth.py
bot/i18n/locales/en.json
bot/i18n/locales/ru.json
bot/llm/adapter.py
bot/main.py
tests/test_llm_config.py
tests/test_llm_schema.py
tests/test_growth_invite.py
tests/test_monetization_copy.py
docs/GROWTH_PLAYBOOK_2026-08-15.md
```

The worktree also contains `.moira-video-analysis/`, which is an audit/video artifact and must not enter the release artifact. Production SQLite files, `.env`, logs, lock files, signed media URLs and user-owned data must remain excluded from any release commit.

## Migrations and assets

The tracked migrations currently include:

| Migration | Role |
|---|---|
| `0002_growth.py` | Growth/referral fields and tables |
| `0003_product_readiness.py` | Product-readiness fields |
| `0004_voice_input.py` | Voice input support |
| `0005_growth_attribution.py` | Growth attribution fields |

The current Git index contains **78 tracked card images** (`assets/cards/c01.jpg` through the deck inventory) and the previous static audit confirms the complete 78-card content/asset set. The current worktree therefore does not reproduce the historical “missing 78 assets” blocker.

## Test inventory

`pytest --collect-only -q` currently reports **115 tests collected** and the clean RC runs **115 passed**. The known post-growth reference was 116 passed. The one-test reduction is explicit: during TASK 0, the obsolete `invite_menu_kb` test was removed because the duplicate `growth.router` implementation was removed and `payment.py` was confirmed as the sole active `cb_invite` owner. The remaining helper, payment, growth and product paths are covered by the current suite; this is not a silent decrease. After routing normalization, the targeted growth/payment/product regression suite reports **12 passed**.

The final full regression and fresh-install evidence belong to TASK 2 and must be recorded separately; unit collection alone is not a live Telegram release gate.

## Active invite routing

The current worktree contains exactly one active callback route for `callback_data="invite"`:

```text
bot/handlers/payment.py:42  @router.callback_query(F.data == "invite")
```

`bot/main.py` registers `payment.router` once and does not register a second `growth.router`. `bot/handlers/growth.py` is helper-only: it contains stable `invite_variant`, `referral_deeplink` and privacy-safe `telegram_share_url` helpers. `payment.py` remains the sole owner of the callback implementation and uses these helpers. This resolves the earlier ambiguity without creating duplicate handlers.

The route uses the existing referral model and payment reward-after-first-purchase rule. Attribution is limited to the stable variant and referral identifiers; raw questions, interpretations and other private reading content are not part of the share URL or analytics properties.

## Historical findings

| Historical finding | Current status | Evidence |
|---|---|---|
| Missing 78 card assets in old checkout | **RESOLVED/HISTORICAL** | Current tracked asset count is 78; static content audit and current test inventory pass. |
| Earlier circular import/test-collection failure | **RESOLVED/HISTORICAL** | Current collection reaches 116 tests and targeted payment/growth tests pass. |
| Invite CTA / active handler ambiguity | **RESOLVED in current worktree** | Exactly one active route in `payment.py`; no duplicate growth router. |
| Live Telegram E2E | **OPEN / NOT YET VERIFIED** | Requires TASK 3 controlled bot/account evidence. |
| Real LLM vs fallback quality | **OPEN / TASK 4** | Existing structural fallback evaluation is insufficient for the new 24-case blind rubric. |
| Mobile iOS/Android delivery QA | **OPEN / TASK 6** | Must not be marked PASS from desktop preview. |

## Decision

TASK 0 is **PASS**. Proceed to TASK 1 only after retaining this report as a release artifact and keeping the audit/video directory outside the release commit. No public deployment or beta launch is authorized by this baseline alone.
