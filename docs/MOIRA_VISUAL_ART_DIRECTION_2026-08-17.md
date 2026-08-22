# Moira visual art direction and autonomous production backlog

Дата: 2026-08-17
Статус: internal design direction; no publication or beta launch authorized

## Brand idea

> **Moira is not a random card generator. It is a small night ritual that turns a question into one visible thread and one grounded next step.**

The visual system must make this promise legible within two seconds. The user should recognize three things immediately: a card was intentionally drawn, the cards belong to Moira, and the result is safe to share without revealing the private question.

## Direction: “Nocturnal Thread”

The recommended direction is **Nocturnal Thread**: a deep indigo ritual space with a warm metallic thread that visually connects the three positions. It is mystical without becoming horror, occult shock, or generic zodiac decoration. The thread is a repeatable signature: it can appear as a fine curved line behind the cards, a crescent seal, a glowing knot at the synthesis point, or a short animation connecting positions.

| System layer | Direction | Why it matters |
|---|---|---|
| Base atmosphere | Near-black plum and indigo, with a subtle vertical or radial depth gradient | Retains current readability while making the canvas feel like a place rather than a flat background |
| Ritual material | A matte altar plane, faint paper grain, soft velvet or obsidian surface, restrained edge vignette | Adds tactile presence without obscuring source card illustrations |
| Signature accent | Aged gold for upright/clarity states; muted rose-metal for reversed/shadow states; pale moon-lilac for text | Creates a brand-owned visual grammar and makes orientation meaningful |
| Signature symbol | Minimal crescent + eye + thread sigil, used sparingly in title/footers and as a watermark-safe seal | Builds recognition across shares, bot outputs, and video frames |
| Light | One soft overhead moon key plus small card halos; no uncontrolled neon bloom | Preserves hierarchy and keeps cards readable on Telegram screens |
| Motion | Slow reveal, 180° card turn, thread connection, then a calm settle | Answers user desire for ritual pacing without making the flow slow or theatrical |
| Typography | PT Serif for oracle authority, paired only where necessary with a neutral sans-serif for controls and metadata | Keeps Russian and English readable while retaining an editorial mystical voice |
| Texture | Fine grain and sparse constellation marks generated deterministically | Prevents repeated starfield sameness while preserving low file size and reproducibility |

## Color tokens proposal

| Token | Hex | Use |
|---|---:|---|
| `moira-void` | `#090611` | Deepest background and footer field |
| `moira-night` | `#17102E` | Primary background gradient |
| `moira-plum` | `#2B1745` | Secondary atmospheric bloom |
| `moira-moon` | `#F2ECFF` | Main title and high-contrast text |
| `moira-lilac` | `#CFC2E6` | Position labels and secondary copy |
| `moira-gold` | `#D8B86A` | Upright frame, thread, seal, focal highlights |
| `moira-rose` | `#B76F89` | Reversed/shadow frame and shadow-state accents |
| `moira-ink` | `#0D0918` | Matte/inset surface around cards |
| `moira-mist` | `#8F7EAE` | Footer and low-priority metadata |

The existing palette already satisfies the broad direction, so the first implementation should refine materials, depth, thread, seal, and layout rather than rewrite all color values. Gold and rose should remain accents below the text luminance; the cards are the semantic focal point.

## Layout system by output

| Output | Visual job | Required hierarchy | High-impact change |
|---|---|---|---|
| Portrait spread, 1080 × 1500 | Make the reading feel like a complete ritual scene | Title → thread/altar → three cards → names/orientation → small brand seal | Replace the large empty lower half with a subtle altar horizon, a synthesis glow, and a compact “thread” footer rather than adding more text |
| Square share, 1080 × 1080 | Earn a pause and a share without exposing private context | Title → three cards → one takeaway → seal/brand | Add a distinctive seal and controlled thread line; keep the takeaway short and move the footer into a quiet branded lockup |
| Single card, 1080 × 1350 | Spotlight one archetype or daily draw | Header → large card → one symbolic subtitle → seal | Add a moon-disc or altar plane behind the card and a card-specific atmospheric color wash |
| Telegram result message | Provide action and continuity | Reading → voice → share/favorite/follow-up/menu | Keep the image clean; use the visual result as the emotional anchor and controls as the practical layer |
| Vertical video, 1080 × 1920 | Stop scroll and demonstrate the ritual | Hook → veil → card reveal → thread → one safe insight → CTA | Use 6–9 seconds, no private question, no promise of certainty, and a fixed signature frame |

## Motion language

The first video/animation pack should use four reusable beats. At 0.0–1.0 seconds, a dark field reveals a single moon glint and the Moira seal. At 1.0–3.0 seconds, a card silhouette emerges through a soft veil and rotates to its orientation. At 3.0–5.5 seconds, a gold or rose thread draws from the card to a small position glyph. At 5.5–8.0 seconds, the card settles while a short, clear insight appears and the final frame carries the Moira mark. Every clip must work muted, use large safe-area typography, and avoid exposing real user questions.

## Asset pack to produce

| Priority | Asset | Format | Purpose | Acceptance criterion |
|---:|---|---|---|---|
| P0 | Moira crescent-eye-thread sigil | SVG/PNG transparent | Brand mark, watermark, video end frame | Recognizable at 48 px and 160 px; no generated text dependency |
| P0 | Altar/velvet background plates | PNG/JPEG, portrait/square/single | Renderer depth layer | Subtle enough that card edges remain dominant |
| P0 | Gold and rose thread overlays | Transparent PNG/SVG | Position connection and orientation cue | Clean alpha, no halo fringe, reusable across layouts |
| P0 | Moon-disc and synthesis glow | Transparent PNG | Focus point behind or below spread | Supports hierarchy without covering card details |
| P1 | Three share-card compositions | PNG/JPEG | Viral-safe Telegram/social outputs | One concise takeaway, no private question, strong brand signature |
| P1 | Three vertical video keyframes | PNG/JPEG | Short-video storyboard and manual/AI motion | Consistent framing across RU/EN and three spread types |
| P1 | Menu/empty-state ornamental panels | PNG | Improve bot menu and history states | Clear function first, ornament second |
| P2 | Optional animated overlays | WebM/MP4 with alpha where supported | Soft reveal, thread draw, dust motes | Must degrade gracefully to static image |

## Autonomous order of work

The work should be executed in this order: first preserve and snapshot the current 78-card source set; second implement renderer-only layers and tokens; third generate the sigil, altar plates, thread overlays, and moon-disc; fourth render portrait, square, and single-card variants; fifth run visual smoke tests and Telegram-size readability checks; sixth prepare private short-video drafts and captions; seventh update the report and stop before publication. This order avoids expensive rework and protects the existing card illustrations.

## Quality gates

A visual change is accepted only if it passes four gates. **Recognition:** the card and its orientation remain immediately readable. **Identity:** the output is recognizably Moira without relying on a large logo. **Clarity:** text remains legible in Telegram preview and no decorative layer competes with the reading. **Safety:** no private question, personal identifier, certainty claim, or manipulative CTA appears in a share or video artifact.

## Explicit non-goals for the overnight pass

Do not replace all source illustrations, create a new full tarot deck, publish videos, connect paid traffic, open the beta cohort, or introduce a complex animation runtime into the Telegram bot. The overnight pass should maximize perceived quality per code change and leave all external distribution behind a human approval gate.

## Sources

The competitive conclusions are based on the companion report [`COMPETITOR_VISUAL_RESEARCH_2026-08-17.md`](COMPETITOR_VISUAL_RESEARCH_2026-08-17.md), which records the source URLs and evidence. The current renderer observations are recorded in [`VISUAL_AUDIT_NOTES_2026-08-17.md`](VISUAL_AUDIT_NOTES_2026-08-17.md).
