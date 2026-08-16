"""layout.py — shared primitives for all display screens.

Canvas: 400×300, BWR palette (BLACK=0, WHITE=1, RED=2).
Legend: 28px white band + 3px BLACK rule → LEGEND_H=31, content starts y=31.
"""

from pathlib import Path
from PIL import Image, ImageFont, ImageDraw  # noqa: F401

# ── font paths ─────────────────────────────────────────────────────────────────
_ASSETS = Path(__file__).parent / "assets" / "fonts"
FONT_JOST_MED  = str(_ASSETS / "Jost-Medium.ttf")
FONT_JOST_SEMI = str(_ASSETS / "Jost-SemiBold.ttf")
FONT_SG_REG    = str(_ASSETS / "SpaceGrotesk-Regular.ttf")

# ── constants ──────────────────────────────────────────────────────────────────
MARGIN   = 16
LEGEND_H = 31     # 28px band + 3px BLACK rule
W, H     = 400, 300
WHITE, BLACK, RED = 0, 1, 2   # Match Inky library: WHITE=0, BLACK=1, RED=2


# ── typography ─────────────────────────────────────────────────────────────────

def draw_tracked(draw, xy, text, font, fill, tracking, anchor_right=None):
    """Draw char-by-char with `tracking` px between glyphs.
    anchor_right: right-align so the run ends at that x.
    Returns x after the last character.
    """
    if anchor_right is not None:
        w = sum(draw.textlength(c, font=font) + tracking for c in text) - tracking
        x = anchor_right - w
    else:
        x = xy[0]
    y = xy[1]
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return x


def _wrap(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], []
    for w in words:
        candidate = " ".join(cur + [w])
        if draw.textlength(candidate, font=font) > max_w and cur:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return lines


def fit_text(draw, text, font_path, sizes, box_w, box_h, line_ratio):
    """Try each size descending; return (font, lines, line_height) that fits.

    Accepts first size where len(lines) * size * line_ratio <= box_h.
    Falls back to smallest with truncation if nothing fits.
    """
    for size in sizes:
        font  = ImageFont.truetype(font_path, size)
        lines = _wrap(draw, text, font, box_w)
        if len(lines) * size * line_ratio <= box_h:
            return font, lines, size * line_ratio
    # Fallback: smallest size, truncate lines to fit
    size  = sizes[-1]
    font  = ImageFont.truetype(font_path, size)
    lh    = size * line_ratio
    lines = _wrap(draw, text, font, box_w)
    while len(lines) > 1 and len(lines) * size * line_ratio > box_h:
        lines.pop()
    # Truncate last line to fit width
    last = lines[-1]
    while draw.textlength(last + "…", font=font) > box_w and len(last) > 1:
        last = last[:-1]
    lines[-1] = last + "…"
    return font, lines, lh


def draw_lines(draw, lines, font, fill, x, y, box_w, line_height, align="left"):
    """Draw wrapped lines; returns y at the bottom of the last glyph."""
    a, d = font.getmetrics()
    lh = int(line_height)
    for line in lines:
        lw = draw.textlength(line, font=font)
        if align == "center":
            tx = x + (box_w - lw) // 2
        elif align == "right":
            tx = x + box_w - lw
        else:
            tx = x
        draw.text((tx, y), line, font=font, fill=fill)
        y += lh
    return y - lh + (a + d)


def block_height(lines, font, line_height):
    """Total pixel height of a text block (top of first ascender to bottom of last descender)."""
    if not lines:
        return 0
    a, d = font.getmetrics()
    return int(line_height) * (len(lines) - 1) + (a + d)


# ── dither ─────────────────────────────────────────────────────────────────────

def dither_rect(img, box, color_a, color_b, cell):
    """Fill box (x0,y0,x1,y1) with a `cell`-px checkerboard of two palette colors.
    Clamps to image bounds automatically.
    """
    arr = img.load()
    iw, ih = img.size
    x0, y0, x1, y1 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
    x0, x1 = max(0, x0), min(iw, x1)
    y0, y1 = max(0, y0), min(ih, y1)
    for y in range(y0, y1):
        for x in range(x0, x1):
            arr[x, y] = color_a if ((x // cell) + (y // cell)) % 2 == 0 else color_b


# ── canvas factory ─────────────────────────────────────────────────────────────

def get_inky():
    try:
        from inky.auto import auto
        inky = auto()
        assert inky.WIDTH == 400 and inky.HEIGHT == 300, (
            f"Expected 400\xd7300, got {inky.WIDTH}\xd7{inky.HEIGHT}"
        )
        return inky
    except AssertionError:
        raise
    except Exception:
        return _MockInky()


class _MockInky:
    WIDTH, HEIGHT = 400, 300
    WHITE, BLACK, RED = 0, 1, 2

    def set_border(self, c): pass
    def set_image(self, img): self._img = img
    def show(self): pass


def make_canvas(inky):
    img = Image.new("P", (inky.WIDTH, inky.HEIGHT))
    p = [0] * 768
    p[0:3] = [255, 255, 255]   # WHITE (index 0)
    p[3:6] = [0,   0,   0  ]   # BLACK (index 1)
    p[6:9] = [220, 20,  20 ]   # RED   (index 2)
    img.putpalette(p)
    return img


def save_preview(img, path):
    img.convert("RGB").save(path)


# ── top legend — shared by all four screens ────────────────────────────────────

_LEGEND = [
    ("A", "ORDET"),
    ("B", "DA/EN"),
    ("C", "RO/DA"),
    ("E", "NYT"),
]
_CELL_W        = 100
_BAND_H        = 28
_RULE_H        = 3   # y 28–31
_LTR_SZ        = 12
_NAME_SZ       = 12
_NAME_TRACKING = 1.7


def draw_legend(draw, active_index):
    """Draw the 28px legend band + 3px BLACK rule. active_index 0–3."""
    # White ground for band
    draw.rectangle((0, 0, W - 1, _BAND_H - 1), WHITE)

    font_ltr  = ImageFont.truetype(FONT_JOST_SEMI, _LTR_SZ)
    font_name = ImageFont.truetype(FONT_JOST_MED,  _NAME_SZ)

    for i, (letter, name) in enumerate(_LEGEND):
        x0, x1   = i * _CELL_W, (i + 1) * _CELL_W
        is_active = (i == active_index)

        if is_active:
            draw.rectangle((x0, 0, x1 - 1, _BAND_H - 1), RED)
            fg = WHITE
        else:
            fg = BLACK

        ltr_w  = draw.textlength(letter, font=font_ltr)
        name_w = (sum(draw.textlength(c, font=font_name) + _NAME_TRACKING
                      for c in name) - _NAME_TRACKING)
        group_w = ltr_w + 6 + name_w   # 6px gap between letter and name

        gx = x0 + (_CELL_W - group_w) / 2   # horizontal centre

        ltr_h  = font_ltr.getmetrics()[0]  + font_ltr.getmetrics()[1]
        name_h = font_name.getmetrics()[0] + font_name.getmetrics()[1]
        gy_ltr  = (_BAND_H - ltr_h)  // 2
        gy_name = (_BAND_H - name_h) // 2

        draw.text((gx, gy_ltr), letter, fg, font=font_ltr)
        draw_tracked(draw, (gx + ltr_w + 6, gy_name), name, font_name, fg,
                     _NAME_TRACKING)

    # BLACK rule y=28–31 (3px)
    draw.rectangle((0, _BAND_H, W - 1, _BAND_H + _RULE_H - 1), BLACK)
