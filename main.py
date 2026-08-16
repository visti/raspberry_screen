import numpy as np
import word_of_the_day
from inky.auto import auto
from PIL import Image, ImageFont, ImageDraw

FONT_HEADER = "/home/visti/.fonts/Bebas.ttf"
FONT_BODY   = "/home/visti/.fonts/Yantramanav-Regular.ttf"

MARGIN    = 18   # horizontal and vertical outer padding
GAP       = 8    # space between elements
DIVIDER_H = 5    # red divider bar height
CORNER_R   = 18   # corner radius for header
DITHER_H   = 40   # height of dithered transition band
DITHER_CELL = 4   # pixels per dither cell (larger = blockier)


# 4×4 Bayer threshold matrix scaled to DITHER_CELL×DITHER_CELL pixel blocks
_BAYER_BASE = np.array([
    [ 0,  8,  2, 10],
    [12,  4, 14,  6],
    [ 3, 11,  1,  9],
    [15,  7, 13,  5],
], dtype=np.float32) / 16.0
BAYER = np.kron(_BAYER_BASE, np.ones((DITHER_CELL, DITHER_CELL)))


def fit_font(path, text, max_w, max_h, draw, max_size=200):
    """Largest font where text fits within max_w × max_h."""
    for size in range(max_size, 8, -1):
        font = ImageFont.truetype(path, size)
        bb = draw.textbbox((0, 0), text, font=font)
        if (bb[2] - bb[0]) <= max_w and (bb[3] - bb[1]) <= max_h:
            return font
    return ImageFont.truetype(path, 8)


def wrap_text(text, font, max_w, draw):
    """Split text into lines that each fit within max_w."""
    words = text.split()
    lines, current = [], []
    for word in words:
        candidate = ' '.join(current + [word])
        bb = draw.textbbox((0, 0), candidate, font=font)
        if (bb[2] - bb[0]) > max_w and current:
            lines.append(' '.join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(' '.join(current))
    return lines


def fit_font_wrapped(path, text, max_w, max_h, draw, max_size=60):
    """Largest font where wrapped text block fits within max_w × max_h."""
    for size in range(max_size, 8, -1):
        font = ImageFont.truetype(path, size)
        lines = wrap_text(text, font, max_w, draw)
        ascent, descent = font.getmetrics()
        line_h = ascent + descent
        total_h = line_h * len(lines) + GAP * (len(lines) - 1)
        if total_h <= max_h:
            return font, lines
    font = ImageFont.truetype(path, 8)
    return font, wrap_text(text, font, max_w, draw)


def block_height(lines, font):
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    return line_h * len(lines) + GAP * (len(lines) - 1)


def draw_text_block(lines, font, color, y, draw, W):
    """Draw centered lines of text, return y after the last line."""
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font)
        x = (W - (bb[2] - bb[0])) // 2
        draw.text((x, y), line, color, font=font)
        y += line_h + GAP
    return y - GAP


def place_y(target_top, font, draw, text):
    """Return draw.text y so that the visible top of text lands at target_top."""
    bb = draw.textbbox((0, 0), text, font=font)
    return target_top - bb[1]


def apply_bayer_dither(img, y_center, band_h, color_top, color_bottom):
    """Symmetric Bayer dither: each color dithers inward from its side toward
    the center, so both sides are visibly dithered with a solid midpoint."""
    palette = img.getpalette()
    arr = np.array(img)
    H, W = arr.shape

    y0 = max(0, y_center - band_h // 2)
    y1 = min(H, y_center + band_h // 2)
    half = band_h / 2

    tile_h = BAYER.shape[0]
    tile_w = BAYER.shape[1]
    for y in range(y0, y1):
        row = BAYER[y % tile_h]
        thresholds = np.tile(row, (W // tile_w) + 1)[:W]
        # dot_density: 0 at edges (no dots) → 0.5 at center (50% dots)
        d = abs(y - y_center) / half
        dot_density = (1.0 - d) * 0.5
        if y < y_center:
            # Black background, red dots grow toward center
            arr[y] = np.where(dot_density > thresholds, color_bottom, color_top)
        else:
            # Red background, black dots grow toward center
            arr[y] = np.where(dot_density > thresholds, color_top, color_bottom)

    out = Image.fromarray(arr, 'P')
    out.putpalette(palette)
    return out


# ── data ──────────────────────────────────────────────────────────────────────

danish, english, _romanian = word_of_the_day.get_word()
danish_word = danish[0]
danish_sent = danish[1]

# ── display setup ─────────────────────────────────────────────────────────────

inky_display = auto()
inky_display.set_border(inky_display.RED)

W, H = inky_display.WIDTH, inky_display.HEIGHT
inner_w = W - MARGIN * 2

img = Image.new("P", (W, H))
draw = ImageDraw.Draw(img)

# ── layout regions ────────────────────────────────────────────────────────────
#
#   ╭─────────────────────────────────╮  ↑
#   │  WHITE  — header words          │  header_h   (rounded bottom corners)
#   ╰═════════════════════════════════╯  DIVIDER_H (red)
#   │  BLACK  — Danish sentence       │
#   ░░░░░░ dithered transition ░░░░░░░░
#   │  RED    — English sentence      │  body_h
#   └─────────────────────────────────┘  ↓

header_h = int(H * 0.55)
body_h   = H - header_h - DIVIDER_H

# Fill entire image red so rounded header corners bleed into red
draw.rectangle((0, 0, W, H), inky_display.RED)

# White header — rounded bottom corners, square top corners
draw.rounded_rectangle((0, 0, W, header_h), radius=CORNER_R, fill=inky_display.WHITE)
draw.rectangle((0, 0, CORNER_R, CORNER_R), inky_display.WHITE)      # square top-left
draw.rectangle((W - CORNER_R, 0, W, CORNER_R), inky_display.WHITE)  # square top-right

# Red divider
draw.rectangle((0, header_h, W, header_h + DIVIDER_H), inky_display.RED)

# ── header: size both words to share the available height ────────────────────

available_h = header_h - MARGIN * 2 - GAP
dk_max_h    = int(available_h * 0.58)
en_max_h    = available_h - dk_max_h

font_dk = fit_font(FONT_HEADER, danish_word, inner_w, dk_max_h, draw)
font_en = fit_font(FONT_HEADER, english[0],  inner_w, en_max_h, draw)

dk_y = place_y(MARGIN, font_dk, draw, danish_word)
dk_bb = draw.textbbox((0, 0), danish_word, font=font_dk)
dk_x  = (W - (dk_bb[2] - dk_bb[0])) // 2
draw.text((dk_x, dk_y), danish_word, inky_display.BLACK, font=font_dk)

dk_visible_bottom = MARGIN + (dk_bb[3] - dk_bb[1])
en_y  = place_y(dk_visible_bottom + GAP, font_en, draw, english[0])
en_bb = draw.textbbox((0, 0), english[0], font=font_en)
en_x  = (W - (en_bb[2] - en_bb[0])) // 2
draw.text((en_x, en_y), english[0], inky_display.RED, font=font_en)

# ── body: wrap sentences ──────────────────────────────────────────────────────

body_top   = header_h + DIVIDER_H
inner_body = body_h - MARGIN * 2
half_body  = (inner_body - GAP) // 2

font_dk_sent, dk_lines = fit_font_wrapped(FONT_BODY, danish_sent, inner_w, half_body, draw)
font_en_sent, en_lines = fit_font_wrapped(FONT_BODY, english[1],  inner_w, half_body, draw)

dk_block_h    = block_height(dk_lines, font_dk_sent)
red_section_y = body_top + MARGIN + dk_block_h + GAP * 2

# Draw red section background
draw.rectangle((0, red_section_y, W, H), inky_display.RED)

# Center Danish sentence in the black region, accounting for 180° rotation.
# On screen the black region runs from screen y=(H - red_section_y + DITHER_H//2)
# down to screen y=(H - body_top). Convert desired screen position back to canvas y.
dk_block_h          = block_height(dk_lines, font_dk_sent)
black_screen_top    = H - red_section_y + DITHER_H // 2
black_screen_bottom = H - body_top
available_black     = black_screen_bottom - black_screen_top
dk_screen_top       = black_screen_top + (available_black - dk_block_h) // 2
dk_y                = H - dk_screen_top - dk_block_h
draw_text_block(dk_lines, font_dk_sent, inky_display.WHITE, dk_y, draw, W)
# Center English sentence in the red region, accounting for 180° rotation.
# On screen (after rotation): red region runs from screen y=0 to
# screen y = H - red_section_y - DITHER_H//2.
# Canvas y maps to screen y as: screen_y = H - canvas_y - block_h.
en_block_h         = block_height(en_lines, font_en_sent)
available_screen_h = H - red_section_y - DITHER_H // 2
screen_top         = (available_screen_h - en_block_h) // 2
en_y               = H - screen_top - en_block_h
draw_text_block(en_lines, font_en_sent, inky_display.WHITE, en_y, draw, W)

# ── dithered transition between black and red ─────────────────────────────────

img = apply_bayer_dither(img, red_section_y, DITHER_H, inky_display.BLACK, inky_display.RED)

# ── push to display ───────────────────────────────────────────────────────────

inky_display.set_image(img)
inky_display.show()
