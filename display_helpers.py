"""display_helpers.py — shared drawing utilities for Inky BWR displays.

Palette indices: BLACK=0, WHITE=1, RED=2.
"""

from pathlib import Path
from PIL import Image, ImageFont, ImageDraw

ASSETS = Path(__file__).parent / "assets" / "fonts"
FONT_BEBAS    = str(ASSETS / "BebasNeue-Regular.ttf")
FONT_BODY_REG = str(ASSETS / "Yantramanav-Regular.ttf")
FONT_BODY_MED = str(ASSETS / "Yantramanav-Medium.ttf")
FONT_FALLBACK = "/usr/share/fonts/TTF/DejaVuSans.ttf"  # Romanian diacritic fallback


# ── typography helpers ────────────────────────────────────────────────────────

def draw_tracked(draw, xy, text, font, fill, tracking):
    """Draw text with extra per-character tracking (px)."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return x


def _wrap(draw, text, font, max_w):
    """Word-wrap text to fit max_w pixels. Returns list of lines."""
    words = text.split()
    lines, current = [], []
    for word in words:
        candidate = " ".join(current + [word])
        if draw.textlength(candidate, font=font) > max_w and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def _block_h(lines, font, line_spacing):
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    leading = int(line_h * line_spacing)
    return leading * (len(lines) - 1) + line_h if lines else 0


def fit_text(draw, text, font_path, sizes, box_w, box_h, line_spacing=1.2):
    """Try each size descending; return (font, lines) that fits box_h.

    Falls back to smallest size with truncation (…) if nothing fits.
    """
    for size in sizes:
        font = ImageFont.truetype(font_path, size)
        lines = _wrap(draw, text, font, box_w)
        if _block_h(lines, font, line_spacing) <= box_h:
            return font, lines
    # Fallback: smallest size, truncate last line
    font = ImageFont.truetype(font_path, sizes[-1])
    lines = _wrap(draw, text, font, box_w)
    while lines and _block_h(lines, font, line_spacing) > box_h:
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > box_w:
            last = last[:-1]
        lines[-1] = last + "…"
        if len(lines) > 1 and _block_h(lines, font, line_spacing) > box_h:
            lines.pop()
        else:
            break
    return font, lines


def draw_lines(draw, lines, font, fill, x, y, box_w, line_spacing, align="left"):
    """Draw wrapped lines; return y after the last baseline."""
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    leading = int(line_h * line_spacing)
    for line in lines:
        lw = draw.textlength(line, font=font)
        if align == "center":
            tx = x + (box_w - lw) // 2
        elif align == "right":
            tx = x + box_w - lw
        else:
            tx = x
        draw.text((tx, y), line, font=font, fill=fill)
        y += leading
    return y - leading + line_h   # bottom of last line


# ── dither helper ─────────────────────────────────────────────────────────────

def dither_rect(img, box, color_a, color_b, cell=3):
    """Fill box (x0,y0,x1,y1) with a checkerboard of color_a/color_b."""
    arr = img.load()
    x0, y0, x1, y1 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
    for y in range(y0, y1):
        for x in range(x0, x1):
            if ((x // cell) + (y // cell)) % 2 == 0:
                arr[x, y] = color_a
            else:
                arr[x, y] = color_b


# ── Inky mock for offline rendering ──────────────────────────────────────────

class MockInky:
    """Stand-in for inky.auto() when running outside the Pi."""
    WIDTH  = 640
    HEIGHT = 400
    BLACK  = 0
    WHITE  = 1
    RED    = 2

    def set_border(self, color):
        pass

    def set_image(self, img):
        self._img = img

    def show(self):
        pass

    @property
    def palette(self):
        p = [255, 255, 255] * 256
        p[0*3:0*3+3] = [0,   0,   0  ]   # BLACK
        p[1*3:1*3+3] = [255, 255, 255]   # WHITE
        p[2*3:2*3+3] = [220, 20,  20 ]   # RED
        return p


def get_inky():
    """Return real or mock Inky depending on environment."""
    try:
        from inky.auto import auto
        return auto()
    except Exception:
        return MockInky()


def make_canvas(inky):
    """Create a P-mode PIL image with the Inky palette."""
    img = Image.new("P", (inky.WIDTH, inky.HEIGHT))
    p = [0] * 768
    p[0*3:0*3+3] = [0,   0,   0  ]
    p[1*3:1*3+3] = [255, 255, 255]
    p[2*3:2*3+3] = [220, 20,  20 ]
    img.putpalette(p)
    return img


def save_preview(img, path):
    """Save palette image as RGB PNG for eyeball check."""
    img.convert("RGB").save(path)
