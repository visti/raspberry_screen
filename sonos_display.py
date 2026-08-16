import urllib.request
from io import BytesIO

import numpy as np
import soco
from inky.auto import auto
from PIL import Image, ImageFont, ImageDraw

FONT_HEADER = "/home/visti/.fonts/Bebas.ttf"
FONT_BODY   = "/home/visti/.fonts/Yantramanav-Regular.ttf"

MARGIN = 16
GAP    = 8


# ── helpers ───────────────────────────────────────────────────────────────────

def fit_font(path, text, max_w, max_h, draw, max_size=150):
    for size in range(max_size, 8, -1):
        font = ImageFont.truetype(path, size)
        bb = draw.textbbox((0, 0), text, font=font)
        if (bb[2] - bb[0]) <= max_w and (bb[3] - bb[1]) <= max_h:
            return font
    return ImageFont.truetype(path, 8)


def wrap_text(text, font, max_w, draw):
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


def fit_font_wrapped(path, text, max_w, max_h, draw, max_size=80):
    for size in range(max_size, 8, -1):
        font = ImageFont.truetype(path, size)
        lines = wrap_text(text, font, max_w, draw)
        ascent, descent = font.getmetrics()
        line_h = ascent + descent
        total_h = line_h * len(lines) + GAP * (len(lines) - 1)
        max_line_w = max(draw.textbbox((0, 0), l, font=font)[2] for l in lines)
        if total_h <= max_h and max_line_w <= max_w:
            return font, lines
    font = ImageFont.truetype(path, 8)
    return font, wrap_text(text, font, max_w, draw)


def draw_lines(lines, font, color, x_center, y, draw):
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font)
        draw.text((x_center - (bb[2] - bb[0]) // 2, y), line, color, font=font)
        y += line_h + GAP
    return y - GAP


def block_h(lines, font):
    ascent, descent = font.getmetrics()
    lh = ascent + descent
    return lh * len(lines) + GAP * (len(lines) - 1)


# ── Sonos ─────────────────────────────────────────────────────────────────────

def discover_speaker():
    try:
        speakers = list(soco.discover(timeout=5) or [])
        return speakers[0] if speakers else None
    except Exception:
        return None


def get_now_playing(speaker):
    info = speaker.get_current_track_info()
    return {
        'artist': info.get('artist', '').strip(),
        'title':  info.get('title',  '').strip(),
        'album':  info.get('album',  '').strip(),
        'art_uri': info.get('album_art', ''),
    }


def fetch_album_art(uri, speaker_ip):
    if not uri:
        return None
    if not uri.startswith('http'):
        uri = f'http://{speaker_ip}:1400{uri}'
    try:
        req = urllib.request.Request(uri, headers={'User-Agent': 'inky-display/1.0'})
        with urllib.request.urlopen(req, timeout=8) as r:
            return Image.open(BytesIO(r.read())).convert('RGB')
    except Exception:
        return None


def dither_art(art_img, size, white_idx, black_idx):
    """Resize and Floyd-Steinberg dither album art to B&W palette indices."""
    # Crop to square (center crop)
    w, h = art_img.size
    side = min(w, h)
    art_img = art_img.crop(((w - side) // 2, (h - side) // 2,
                             (w + side) // 2, (h + side) // 2))
    art_img = art_img.resize((size, size), Image.LANCZOS)
    bw = art_img.convert('L').convert('1', dither=Image.FLOYDSTEINBERG)
    arr = np.array(bw)   # True = white, False = black
    return np.where(arr, white_idx, black_idx).astype(np.uint8)


# ── display ───────────────────────────────────────────────────────────────────

def show_error(inky_display, img, draw, message):
    W, H = inky_display.WIDTH, inky_display.HEIGHT
    font = ImageFont.truetype(FONT_BODY, 22)
    bb = draw.textbbox((0, 0), message, font=font)
    draw.text(((W - (bb[2]-bb[0])) // 2, (H - (bb[3]-bb[1])) // 2),
              message, inky_display.BLACK, font=font)
    inky_display.set_image(img)
    inky_display.show()


def show():
    inky_display = auto()
    inky_display.set_border(inky_display.WHITE)

    W, H = inky_display.WIDTH, inky_display.HEIGHT

    img = Image.new("P", (W, H))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, H), inky_display.WHITE)

    # ── layout ────────────────────────────────────────────────────────────────
    #
    #   ┌──────────────┬───────────────────────────┐
    #   │              │  ARTIST NAME              │  BLACK bg throughout
    #   │  Album Art   ┃                           │
    #   │  (B&W dither)┃  Track Title              │
    #   │              ┃  (large, red)             │
    #   │              │                           │
    #   │              │  Album Name               │
    #   └──────────────┴───────────────────────────┘
    #        210px      ┃         190px
    #                  red divider

    ART_SIZE  = 190
    SEP_X     = MARGIN + ART_SIZE + MARGIN      # x of red separator
    TEXT_X    = SEP_X + 6                       # left edge of text area
    TEXT_W    = W - TEXT_X - MARGIN             # text area width
    TEXT_CX   = TEXT_X + TEXT_W // 2            # center x for text

    # ── Sonos data ────────────────────────────────────────────────────────────
    speaker = discover_speaker()
    if speaker is None:
        show_error(inky_display, img, draw, "No Sonos speaker found")
        return

    track = get_now_playing(speaker)
    if not track['title']:
        show_error(inky_display, img, draw, "Nothing playing")
        return

    # ── Album art ─────────────────────────────────────────────────────────────
    art_img = fetch_album_art(track['art_uri'], speaker.ip_address)
    if art_img:
        palette = img.getpalette()
        art_arr = dither_art(art_img, ART_SIZE,
                             inky_display.WHITE, inky_display.BLACK)
        main_arr = np.array(img)
        art_y = (H - ART_SIZE) // 2
        main_arr[art_y:art_y + ART_SIZE, MARGIN:MARGIN + ART_SIZE] = art_arr
        img = Image.fromarray(main_arr, 'P')
        img.putpalette(palette)
        draw = ImageDraw.Draw(img)

    # Red vertical separator
    draw.rectangle((SEP_X, MARGIN, SEP_X + 3, H - MARGIN), inky_display.RED)

    # ── Text ──────────────────────────────────────────────────────────────────
    # Allocate vertical space: artist 20%, title 50%, album 20%, gaps the rest
    text_h = H - MARGIN * 2
    artist_max_h = int(text_h * 0.20)
    title_max_h  = int(text_h * 0.50)
    album_max_h  = int(text_h * 0.20)

    font_artist, artist_lines = fit_font_wrapped(FONT_BODY,   track['artist'], TEXT_W, artist_max_h, draw, max_size=40)
    font_title,  title_lines  = fit_font_wrapped(FONT_HEADER, track['title'],  TEXT_W, title_max_h,  draw, max_size=80)
    font_album,  album_lines  = fit_font_wrapped(FONT_BODY,   track['album'],  TEXT_W, album_max_h,  draw, max_size=28) if track['album'] else (None, [])

    total_h = (block_h(artist_lines, font_artist) + GAP * 3 +
               block_h(title_lines, font_title) +
               (GAP * 2 + block_h(album_lines, font_album) if album_lines else 0))

    y = MARGIN + (text_h - total_h) // 2

    y = draw_lines(artist_lines, font_artist, inky_display.BLACK, TEXT_CX, y, draw) + GAP * 3
    y = draw_lines(title_lines,  font_title,  inky_display.RED,   TEXT_CX, y, draw)
    if album_lines:
        y += GAP * 2
        draw_lines(album_lines, font_album, inky_display.BLACK, TEXT_CX, y, draw)

    inky_display.set_image(img)
    inky_display.show()


if __name__ == '__main__':
    show()
