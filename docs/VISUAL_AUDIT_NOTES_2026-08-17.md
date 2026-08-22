# Moira visual audit notes — 2026-08-17

## Verified current outputs

### `docs/visual_smoke_outputs/spread_ru.jpg`

The current portrait spread is 1080 × 1500 px. It uses a deep indigo-to-black starfield background, a centered serif title, three evenly spaced cards, position labels above the cards, card names below, and a small MOIRA footer. The source Rider–Waite illustrations remain visibly intact. Upright and reversed states are visually distinguishable through the illustration orientation and a thin frame treatment; the reversed center card also has a rose-colored accent frame.

The main strengths are immediate card recognition, strong contrast, clear three-position hierarchy, and a coherent night-sky atmosphere. The main weaknesses are large unused lower-half space, a relatively generic starfield, limited depth/material cues, and weak visual signature beyond the card frame and title. The card images dominate the experience while Moira’s own mystical identity remains understated.

### `docs/visual_smoke_outputs/share_ru.jpg`

The current square share output is 1080 × 1080 px. It preserves the same indigo starfield, title, three-card arrangement, card labels, a single short takeaway line, and MOIRA TAROT footer. It is legible and suitable as a baseline Telegram share card.

The main strengths are compact hierarchy, readable card labels, and a share-safe short message without visible private question text. The main weaknesses are a generic background, limited emotional focal point, lack of a distinctive Moira sigil or ritual object, and insufficient social-hook design. The share square should become the primary viral asset format: stronger first-glance symbolism, a signature seal, one concise insight, and a consistent CTA-safe footer.

## Design implications

Preserve the 78 source card illustrations and improve the renderer layer rather than replacing the deck. Prioritize a recognizable Moira visual system: ritual tabletop or celestial altar depth, restrained gold/rose-metal accents, a recurring crescent/eye/thread sigil, controlled glow, stronger card-to-background separation, and variants optimized separately for portrait reading, square sharing, and short vertical video.

## Generated asset QA checkpoint

The generated sigil and thread overlay were viewed at full size. Both visibly contain a strong green chroma/key background and green fringe/artifacts rather than clean usable alpha in the preview. They are **not accepted for renderer integration as-is**. The gold/rose subject concept is directionally useful, but the assets must be regenerated with a clean dark background and then deterministically keyed/validated, or recreated as vector/deterministic overlays. This prevents green contamination of Telegram outputs.

## Cleaned overlay QA checkpoint

The deterministic chroma cleanup materially improved the sigil: the bright green key color is removed and the gold/rose emblem is visually usable against dark backgrounds, although faint dark fringe/line remnants should be tested on the final palette. The cleaned thread overlay remains contaminated by broad dark-green texture and fragmented transparency; it is **rejected for direct compositing**. For production, the thread should be recreated as a deterministic vector/Pillow line overlay or regenerated on a plain dark matte and keyed with a narrower subject mask. The altar and share background plates remain the preferred usable generated assets from this pack.

## Integrated renderer smoke QA

### New portrait spread

The generated altar plate materially improves Moira’s identity: the scene now feels tactile, nocturnal, and ritual rather than a generic gradient. The source cards remain the focal point and are still readable. The current improvement exposes one layout issue: the altar’s central eye/line motif sits behind the title and the position labels, creating some visual competition around the center card. The portrait footer sigil is legible and feels brand-owned. Next refinement should lower or dim the background motif behind text, not remove the altar layer.

### New square share

The square share output is a strong improvement for social/Telegram use. The thin celestial border, altar texture, centered synthesis motif, roses, and footer sigil create a distinctive share artifact while keeping the three cards readable. The thread and eye motif now acts as a visual bridge between cards and takeaway. The remaining issue is density in the lower third: the motif and footer are slightly crowded, so a small reduction in motif opacity/scale or more footer breathing room would improve hierarchy.
