# Sibyl-informed Moira product decisions

Research date: 2026-08-10. Sources are public marketing, store listings,
terms, privacy policy and reviews; they are not evidence of Sibyl's internal
architecture.

| Idea | Public evidence | Moira state | Decision | Implementation |
|---|---|---|---|---|
| Broad spiritual AI modes | Sibyl markets metaphysical/wellness questions, visualisations, stories and Metametrics. | Tarot-first bot | Do not copy | Deferred: no generic spiritual assistant, datasets or model router. |
| Guidance before a question | Product positioning emphasises guided spiritual use. | Generic prompt existed. | Adopt now | Spread-specific RU/EN question guidance for Situation, Love and Choice. |
| Continue after an answer | App products emphasise ongoing, personal use; implementation is not public. | Footer ended at share/favourite/menu. | Adopt now | Saved-reading follow-up reuses cards, positions and question lens; it does not draw random cards or open free chat. |
| History as a return loop | App-store reviews value convenience and retaining prior paid work. | List and favourites existed. | Adopt now | Journal list opens the full saved reading with cards, question, interpretation and actions. |
| Output rating | Store reviews are a direct quality signal; no internal Sibyl feedback system is verified. | Event infrastructure existed. | Adopt now | 👍/👎 event with reading ID, spread and LLM/fallback mode; no question text. |
| Voice and sharing | Sibyl advertises media/visual features. | Voice fallback and share already existed. | Keep, verify | No rewrite; share now uses a privacy-safe persisted summary. |
| Trial / quota | Current Sibyl plans market question quotas; one public Play review criticises paywall timing. | FREE_READINGS, promo, early-bird and Stars existed. | Configure now | Invite-only FREE_READINGS=10 in example/runbook; no permanent hardcode or payment redesign. |
| Personalisation | Sibyl claims tailored profiles/Metametrics. | Language, altar, birth date, history and weekly mirror exist. | Keep bounded | Use existing first-party context only; no new sensitive profiler. |

## Evidence classification

- **Verified fact:** Sibyl's public site advertises monthly plans with question,
  visualisation, story and Metametrics allowances; its terms and privacy policy
  say it processes prompts/inputs and outputs. Its App Store and Google Play
  listings show a mobile product and in-app purchases.
- **Vendor claim:** Sibyl describes its models as trained on metaphysical wisdom
  and its outputs as sophisticated/personalised. Those claims do not prove a
  particular dataset, RAG system, agent framework, or model router.
- **Not verified:** an official open-source Sibyl application repository or
  public technical implementation description. No proprietary code, prompts,
  interface, assets, or authentication flows are used by Moira.

## Deliberately deferred backlog

Dream visualiser, storyteller, face swap, AI-to-AI, broad spiritual datasets,
proprietary-style routing, vector database, standalone mobile app, Discord,
generic image generation, and deterministic future-trajectory claims remain
out of scope. Moira stays a Telegram Tarot companion.
