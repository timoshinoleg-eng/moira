"""Design tokens for Moira's visual system.

Single source of truth for colors, fonts, canvas sizes, typography, spacing
and decorative parameters used by ``bot/visual/render.py`` — no magic numbers
in Pillow code.

Font rationale (verified with fontTools cmap, 2026-08-07):
PT Serif (SIL OFL 1.1, ParaType) covers core Cyrillic (А-я + Ёё) and Basic
Latin, but NOT decorative symbols (U+2726 star, U+27F2 anticlockwise arrow,
U+2605 star, emoji, geometric shapes). The renderer therefore sanitizes such
glyphs (see ``render._sanitize_text``) and reversed-card markers use localized
words instead of symbols.
"""
from __future__ import annotations

# --------------------------------------------------------------- colors ----
BG_TOP = (30, 18, 58)              # canvas gradient: top
BG_BOTTOM = (6, 4, 14)             # canvas gradient: bottom
TEXT_TITLE = (240, 235, 255)       # titles / headlines
TEXT_PRIMARY = (250, 246, 255)     # card names, main captions
TEXT_SECONDARY = (225, 218, 245)   # share summary
TEXT_POSITION = (205, 195, 235)    # spread position labels
TEXT_FOOTER = (150, 140, 180)      # footer brand line
TEXT_REVERSED = (190, 170, 215)    # reversed-card note
GLOW_COLOR = (140, 100, 210, 30)   # card halo (RGBA)
PLACEHOLDER_FILL = (24, 18, 44)    # missing-asset panel fill
PLACEHOLDER_OUTLINE = (120, 95, 170)  # missing-asset panel border

# ----------------------------------------------------------------- fonts ---
FONT_REGULAR = "PT_Serif-Web-Regular.ttf"
FONT_BOLD = "PT_Serif-Web-Bold.ttf"
FONT_FALLBACK_REGULAR = "DejaVuSans.ttf"
FONT_FALLBACK_BOLD = "DejaVuSans-Bold.ttf"

# Reversed-card note under the card name (bilingual).
REVERSED_NOTE = {"ru": "перевёрнутая", "en": "reversed"}
# Reversed marker on share cards (no symbol: PT Serif lacks U+27F2; the
# localized word is unambiguous and font-safe).
SHARE_REVERSED_MARKER = {"ru": " (перевёрнутая)", "en": " (reversed)"}

# ---------------------------------------------------------- canvas sizes ----
CANVAS_SPREAD = (1080, 1500)   # 3-card reading photo
CANVAS_SHARE = (1080, 1080)    # square share card
CANVAS_SINGLE = (1080, 1350)   # single card / altar / quiz result

# ------------------------------------------------------------- typography ----
FONT_SPREAD_TITLE = 46
FONT_SPREAD_POSITION = 26
FONT_SPREAD_NAME = 27
FONT_SPREAD_NOTE = 21
FONT_SPREAD_FOOTER = 22
FONT_SHARE_TITLE = 44
FONT_SHARE_POSITION = 22
FONT_SHARE_NAME = 22
FONT_SHARE_SUMMARY = 28
FONT_SHARE_FOOTER = 24
FONT_SINGLE_HEADER = 48
FONT_SINGLE_SUBTITLE = 34
FONT_SINGLE_FOOTER = 22

# ----------------------------------------------------------------- layout ----
# spread
SPREAD_CARD_SIZE = (300, 520)
SPREAD_CARD_GAP = 42
SPREAD_TITLE_Y = 64
SPREAD_CARDS_Y = 330
SPREAD_LABEL_OFFSET_Y = -44
SPREAD_NAME_OFFSET_Y = 18
SPREAD_NOTE_OFFSET_Y = 54
SPREAD_FOOTER_OFFSET_Y = -110
# share
SHARE_CARD_SIZE = (240, 416)
SHARE_CARD_GAP = 36
SHARE_TITLE_Y = 56
SHARE_TITLE_STEP = 54
SHARE_TITLE_MAX_LINES = 2
SHARE_TITLE_MAX_WIDTH = 1000
SHARE_CARDS_Y = 200
SHARE_LABEL_OFFSET_Y = -34
SHARE_NAME_OFFSET_Y = 12
SHARE_SUMMARY_Y = 740
SHARE_SUMMARY_STEP = 42
SHARE_SUMMARY_MAX_LINES = 4
SHARE_SUMMARY_MAX_WIDTH = 960
SHARE_FOOTER_OFFSET_Y = -64
# single
SINGLE_CARD_SIZE = (430, 745)
SINGLE_HEADER_Y = 70
SINGLE_HEADER_STEP = 58
SINGLE_HEADER_MAX_LINES = 2
SINGLE_HEADER_MAX_WIDTH = 1000
SINGLE_CARDS_Y = 220
SINGLE_SUBTITLE_OFFSET_Y = 36
SINGLE_SUBTITLE_STEP = 46
SINGLE_SUBTITLE_MAX_LINES = 2
SINGLE_SUBTITLE_MAX_WIDTH = 980
SINGLE_FOOTER_OFFSET_Y = -60

# ------------------------------------------------------------ decorations ----
BG_STARS = 170
STAR_RADIUS = (0.4, 1.7)
STAR_ALPHA = (60, 210)
STAR_GOLD_CHANCE = 0.2
STAR_BLUR = 0.4
GLOW_PAD = 36
GLOW_BLUR = 28
PLACEHOLDER_RADIUS = 18
PLACEHOLDER_BORDER_WIDTH = 3

# ---------------------------------------------------------------- output ----
JPEG_QUALITY = 88
CARD_MATTE_PADDING = 9
CARD_MATTE_RADIUS = 26
CARD_MATTE_FILL = (10, 6, 22)
CARD_MATTE_OUTLINE = (92, 67, 123)
CARD_MATTE_WIDTH = 2
CARD_INSET = 4
CARD_FRAME_REVERSED_OUTLINE = (183, 104, 132)
CARD_FRAME_OUTLINE = (214, 182, 118)
CARD_FRAME_WIDTH = 3
CARD_FRAME_RADIUS = 18
