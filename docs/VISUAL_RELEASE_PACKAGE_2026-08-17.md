# Moira visual release package — 2026-08-17

## Status

The overnight visual pass is **implemented locally and technically validated**, but no content was published and no beta cohort was started. The work preserves the existing 78-card illustration source set and changes the renderer layer, background plates, brand overlays, and internal documentation.

## What changed

Moira now has a coherent **Nocturnal Thread** visual direction: deep indigo/plum atmosphere, matte altar material, restrained aged gold, muted rose for shadow/reversed states, and a crescent-eye-thread signature. The portrait spread uses a generated altar plate with a local readability shade over the title zone. The square share output uses a generated share plate, a clean deterministic vector thread, and the accepted clean sigil. The single-card renderer uses the altar plate with a top readability shade and keeps the existing card frame logic.

The generated green-chroma overlays were intentionally rejected after visual QA. The sigil was cleaned deterministically and accepted with traceability; the contaminated thread was replaced by a small deterministic Pillow vector overlay so no green artifacts can enter production images.

## Asset inventory

| Asset | Status | Intended use |
|---|---|---|
| `assets/generated_visuals/2026-08-17/moira_nocturnal_thread_reference.jpg` | Accepted reference | Canonical mood and material reference |
| `assets/generated_visuals/2026-08-17/moira_altar_portrait.jpg` | Accepted | Portrait spread and single-card background |
| `assets/generated_visuals/2026-08-17/moira_share_background.jpg` | Accepted | Square Telegram/social share background |
| `assets/generated_visuals/2026-08-17/moira_sigil_clean.png` | Accepted with minor fringe caution | Footer mark and compact brand signature |
| `assets/generated_visuals/2026-08-17/moira_thread_overlay_vector.png` | Accepted | Clean transparent thread overlay |
| `assets/generated_visuals/2026-08-17/video_drafts/moira_video_keyframe_portrait.jpg` | Accepted keyframe | Portrait video starting frame |
| `assets/generated_visuals/2026-08-17/video_drafts/moira_ritual_reveal_01.mp4` | Technical PASS, draft only | 8-second portrait ritual reveal; do not publish without review |
| `assets/generated_visuals/2026-08-17/moira_sigil.png` | Rejected | Original chroma-key attempt; retained only for audit traceability |
| `assets/generated_visuals/2026-08-17/moira_thread_overlay.png` | Rejected | Original green-texture overlay; retained only for audit traceability |

## QA evidence

`py_compile` passes for the modified renderer and tokens modules. The full project regression remains **119 passed**. `git diff --check` passes. The visual smoke generator produced portrait spread, square share, single reversed, and English spread outputs after integration. The generated video is technically valid H.264/AAC, 720×1280, 8 seconds, and 1.8 MB; it is a draft and was not published.

The visual smoke result now has a tactile altar surface and a distinct Moira footer signature. The remaining improvement is optional refinement of the portrait central motif opacity and lower-third spacing if more time is available; it is not a release-blocking defect for the local pass.

## Short-video storyboard

The current video draft is a muted 8-second ritual reveal. It begins with a still nocturnal altar, introduces a restrained light pulse, turns a blank card, draws an aged-gold thread toward the Moira sigil, and ends on a clean centered frame with a safe caption area. It deliberately contains no user question, private data, spoken claim, certainty promise, or publication action.

## Autonomous continuation plan

The next autonomous work block should be executed in four stages. First, run the visual smoke suite on RU and EN, inspect Telegram-size crops, and confirm that the sigil remains legible at 48–90 px. Second, add one more deterministic background variant and compare it against the current plate using the same spread fixture. Third, prepare three caption-safe video variants: “daily thread,” “three positions,” and “one next step,” with no private content. Fourth, run a human review gate for the portrait, square, single, and video outputs before any GitHub push, Telegram publication, or beta distribution.

The release gate remains separate from visual completion. Visual assets can be ready while TASK 12 remains NO-GO until the outstanding live E2E and provider-quality prerequisites are genuinely closed.

## Related records

- [`COMPETITOR_VISUAL_RESEARCH_2026-08-17.md`](COMPETITOR_VISUAL_RESEARCH_2026-08-17.md)
- [`MOIRA_VISUAL_ART_DIRECTION_2026-08-17.md`](MOIRA_VISUAL_ART_DIRECTION_2026-08-17.md)
- [`VISUAL_AUDIT_NOTES_2026-08-17.md`](VISUAL_AUDIT_NOTES_2026-08-17.md)
- [`LIVE_GATE_REPORT_2026-08-16.md`](LIVE_GATE_REPORT_2026-08-16.md)
