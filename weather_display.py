import json
import math
import urllib.request
from datetime import datetime

from inky.auto import auto
from PIL import Image, ImageFont, ImageDraw

FONT_HEADER = "/home/visti/.fonts/Bebas.ttf"
FONT_BODY   = "/home/visti/.fonts/Yantramanav-Regular.ttf"

MARGIN = 16
GAP    = 8

LAT = 55.6867
LON = 12.4539
N_FORECAST = 6   # forecast days shown after today

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",  2: "Partly cloudy",  3: "Overcast",
    45: "Fog",          48: "Icy fog",
    51: "Light drizzle", 53: "Drizzle",      55: "Heavy drizzle",
    61: "Light rain",   63: "Rain",           65: "Heavy rain",
    71: "Light snow",   73: "Snow",           75: "Heavy snow",
    77: "Snow grains",
    80: "Light showers", 81: "Showers",       82: "Heavy showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm",   99: "Thunderstorm",
}


# ── icon drawing ──────────────────────────────────────────────────────────────

def _cloud(draw, cx, cy, w, h, fill):
    """Filled cloud shape: three bumps on top, flat base."""
    hw, hh = w // 2, h // 2
    # Flat base rectangle
    draw.rectangle((cx - hw, cy - hh // 4, cx + hw, cy + hh // 2), fill=fill)
    # Left bump
    draw.ellipse((cx - hw,        cy - hh // 2,
                  cx - hw // 3,   cy + hh // 4), fill=fill)
    # Centre bump (tallest)
    draw.ellipse((cx - hw // 2,   cy - hh,
                  cx + hw // 2,   cy + hh // 4), fill=fill)
    # Right bump
    draw.ellipse((cx + hw // 5,   cy - hh // 3,
                  cx + hw,        cy + hh // 4), fill=fill)


def _sun(draw, cx, cy, r, fill_disc, fill_ray):
    """Filled circle with eight line rays."""
    disc_r = int(r * 0.52)
    draw.ellipse((cx - disc_r, cy - disc_r, cx + disc_r, cy + disc_r),
                 fill=fill_disc)
    for deg in range(0, 360, 45):
        rad = math.radians(deg)
        r0 = disc_r + 4
        r1 = r
        draw.line(
            (cx + int(r0 * math.cos(rad)), cy + int(r0 * math.sin(rad)),
             cx + int(r1 * math.cos(rad)), cy + int(r1 * math.sin(rad))),
            fill=fill_ray, width=2,
        )


def _draw_icon(draw, wmo_code, cx, cy, size, BLACK, RED, WHITE):
    """Draw a weather icon centred at (cx, cy) fitting in a square of `size`."""
    r   = size // 2
    cw  = int(r * 1.5)    # cloud width
    ch  = int(r * 0.85)   # cloud height

    if wmo_code == 0 or wmo_code == 1:
        # ── clear / mainly clear: large sun ──────────────────────────────
        _sun(draw, cx, cy, r, RED, BLACK)

    elif wmo_code == 2:
        # ── partly cloudy: small offset sun + cloud in front ─────────────
        sx = cx - r // 4
        sy = cy - r // 4
        _sun(draw, sx, sy, int(r * 0.6), RED, BLACK)
        _cloud(draw, cx + r // 5, cy + r // 6, cw, ch, BLACK)
        # white fill to "cut" sun behind cloud
        _cloud(draw, cx + r // 5, cy + r // 6, cw - 4, ch - 4, WHITE)
        _cloud(draw, cx + r // 5, cy + r // 6, cw, ch, BLACK)

    elif wmo_code == 3:
        # ── overcast: solid cloud ─────────────────────────────────────────
        _cloud(draw, cx, cy, cw, ch, BLACK)

    elif wmo_code in (45, 48):
        # ── fog: three tapered horizontal bars ───────────────────────────
        for i, frac in enumerate([1.0, 0.75, 0.5]):
            bw = int(r * 1.8 * frac)
            by = cy - r // 3 + i * (r // 2)
            draw.rectangle((cx - bw // 2, by - 3, cx + bw // 2, by + 3),
                           fill=BLACK)

    elif wmo_code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        # ── rain: cloud + four angled drop lines ─────────────────────────
        cloud_cy = cy - r // 5
        _cloud(draw, cx, cloud_cy, cw, ch, BLACK)
        drop_y0 = cloud_cy + ch // 2 + 4
        for i in range(4):
            x0 = cx - int(r * 0.55) + i * (r // 3)
            draw.line((x0, drop_y0, x0 - r // 8, drop_y0 + r // 3),
                     fill=BLACK, width=2)

    elif wmo_code in (71, 73, 75, 77, 85, 86):
        # ── snow: cloud + five small filled circles ───────────────────────
        cloud_cy = cy - r // 5
        _cloud(draw, cx, cloud_cy, cw, ch, BLACK)
        dot_y = cloud_cy + ch // 2 + r // 4
        for i in range(5):
            dx = cx - int(r * 0.65) + i * (r // 3)
            draw.ellipse((dx - 3, dot_y - 3, dx + 3, dot_y + 3), fill=BLACK)

    else:
        # ── storm (95/96/99): cloud + red lightning bolt ─────────────────
        cloud_cy = cy - r // 4
        _cloud(draw, cx, cloud_cy, cw, ch, BLACK)
        # Lightning polygon
        tip_x = cx + r // 5
        bx    = cx - r // 5
        by0   = cloud_cy + ch // 2
        mid_y = by0 + r // 3
        bot_y = by0 + int(r * 0.75)
        bolt = [
            (tip_x,           by0),
            (bx,              mid_y),
            (cx,              mid_y),
            (bx - r // 8,     bot_y),
            (cx + r // 4,     mid_y + r // 6),
            (cx + r // 8,     mid_y + r // 6),
        ]
        draw.polygon(bolt, fill=RED)


# ── helpers ───────────────────────────────────────────────────────────────────

def _fetch():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,weathercode,windspeed_10m"
        "&daily=temperature_2m_max,temperature_2m_min,weathercode"
        "&timezone=Europe%2FCopenhagen"
        f"&forecast_days={N_FORECAST + 1}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "inky-display/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def _fit_font(path, text, max_w, draw, max_size=180, max_h=None):
    for size in range(max_size, 8, -2):
        font = ImageFont.truetype(path, size)
        bb   = draw.textbbox((0, 0), text, font=font)
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        if w <= max_w and (max_h is None or h <= max_h):
            return font
    return ImageFont.truetype(path, 8)


# ── main display ──────────────────────────────────────────────────────────────

def show():
    inky_display = auto()
    inky_display.set_border(inky_display.WHITE)
    W, H = inky_display.WIDTH, inky_display.HEIGHT
    BLACK, RED, WHITE = inky_display.BLACK, inky_display.RED, inky_display.WHITE

    img  = Image.new("P", (W, H))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, H), WHITE)

    # ── fetch ─────────────────────────────────────────────────────────────────
    try:
        data      = _fetch()
        current   = data["current"]
        daily     = data["daily"]
        temp      = round(current["temperature_2m"])
        wmo_code  = current["weathercode"]
        condition = WMO_CODES.get(wmo_code, "Unknown")
        forecast  = [
            {
                "day": datetime.strptime(daily["time"][i], "%Y-%m-%d").strftime("%a").upper(),
                "hi":  round(daily["temperature_2m_max"][i]),
                "lo":  round(daily["temperature_2m_min"][i]),
            }
            for i in range(1, N_FORECAST + 1)
            if i < len(daily["time"])
        ]
    except Exception:
        font = ImageFont.truetype(FONT_BODY, 22)
        msg  = "Weather unavailable"
        bb   = draw.textbbox((0, 0), msg, font=font)
        draw.text(((W - (bb[2] - bb[0])) // 2, (H - (bb[3] - bb[1])) // 2),
                  msg, BLACK, font=font)
        inky_display.set_image(img)
        inky_display.show()
        return

    now = datetime.now()

    # ── layout anchors ────────────────────────────────────────────────────────
    #
    #  [MARGIN]          header (location + date)
    #  [header_bottom+2] divider
    #  [content_top … content_bottom]  ← icon zone LEFT | temp+cond zone RIGHT
    #  [FORECAST_TOP-2]  divider
    #  [FORECAST_TOP … H-MARGIN]       forecast strip (6 cols)
    #
    FORECAST_TOP = H - H // 3           # = 200 for H=300

    # ── header ────────────────────────────────────────────────────────────────
    font_loc  = ImageFont.truetype(FONT_HEADER, 44)
    font_date = ImageFont.truetype(FONT_BODY, 20)

    loc_str  = "RØDOVRE"
    date_str = now.strftime("%-d %B, %A")

    bb_loc  = draw.textbbox((0, 0), loc_str,  font=font_loc)
    bb_date = draw.textbbox((0, 0), date_str, font=font_date)
    loc_h   = bb_loc[3] - bb_loc[1]

    draw.text((MARGIN, MARGIN), loc_str, RED, font=font_loc)
    date_y = MARGIN + (loc_h - (bb_date[3] - bb_date[1])) // 2
    draw.text((W - MARGIN - (bb_date[2] - bb_date[0]), date_y),
              date_str, BLACK, font=font_date)

    header_bottom = MARGIN + loc_h + GAP
    draw.rectangle((MARGIN, header_bottom, W - MARGIN, header_bottom + 2), RED)

    # ── content zone ──────────────────────────────────────────────────────────
    content_top    = header_bottom + GAP * 2
    content_bottom = FORECAST_TOP - GAP - 2
    content_h      = content_bottom - content_top
    content_cy     = content_top + content_h // 2   # vertical centre of zone

    # Split horizontally at midpoint: LEFT = icon, RIGHT = temp + condition
    split_x     = W // 2                            # x=200
    icon_cx     = (MARGIN + split_x) // 2           # x=108
    text_cx     = (split_x + W - MARGIN) // 2       # x=292
    text_zone_w = W - MARGIN - split_x              # 184px

    # ── icon ──────────────────────────────────────────────────────────────────
    icon_size = min(content_h, split_x - MARGIN) - GAP * 2   # square that fits
    _draw_icon(draw, wmo_code, icon_cx, content_cy, icon_size,
               BLACK, RED, WHITE)

    # ── temperature + condition (centred in right sub-zone) ───────────────────
    temp_str     = f"{temp}\u00b0"
    cond_reserve = 38
    font_temp    = _fit_font(FONT_HEADER, temp_str, text_zone_w, draw,
                             max_size=180, max_h=content_h - cond_reserve - GAP)
    bb_temp      = draw.textbbox((0, 0), temp_str, font=font_temp)
    temp_h       = bb_temp[3] - bb_temp[1]

    font_cond = _fit_font(FONT_BODY, condition, text_zone_w, draw, max_size=30)
    bb_cond   = draw.textbbox((0, 0), condition, font=font_cond)
    cond_h    = bb_cond[3] - bb_cond[1]

    # Centre the temperature in the zone; condition hangs below
    temp_top = content_top + (content_h - temp_h) // 2
    temp_x   = text_cx - (bb_temp[0] + bb_temp[2]) // 2
    draw.text((temp_x, temp_top), temp_str, RED, font=font_temp)

    cond_x = text_cx - (bb_cond[0] + bb_cond[2]) // 2
    draw.text((cond_x, temp_top + temp_h + GAP), condition, BLACK, font=font_cond)

    # ── forecast divider ──────────────────────────────────────────────────────
    draw.rectangle((MARGIN, FORECAST_TOP - 2, W - MARGIN, FORECAST_TOP), RED)

    # ── forecast strip ────────────────────────────────────────────────────────
    n         = len(forecast)
    cell_w    = (W - MARGIN * 2) // n
    strip_top = FORECAST_TOP + GAP
    strip_h   = H - MARGIN - strip_top          # ≈ 76px

    font_day  = ImageFont.truetype(FONT_BODY, 16)
    font_hi   = ImageFont.truetype(FONT_BODY, 22)
    font_lo   = ImageFont.truetype(FONT_BODY, 18)

    # Measure a representative column block for vertical centering
    row_day_h = draw.textbbox((0,0), "MON", font=font_day)[3] - draw.textbbox((0,0), "MON", font=font_day)[1]
    row_hi_h  = draw.textbbox((0,0), "00°", font=font_hi )[3] - draw.textbbox((0,0), "00°", font=font_hi )[1]
    row_lo_h  = draw.textbbox((0,0), "00°", font=font_lo )[3] - draw.textbbox((0,0), "00°", font=font_lo )[1]
    col_block_h = row_day_h + GAP + row_hi_h + GAP // 2 + row_lo_h
    col_y0 = strip_top + max(0, (strip_h - col_block_h) // 2)

    for i, fc in enumerate(forecast):
        cx = MARGIN + i * cell_w + cell_w // 2

        def _draw_col_text(text, font, color, y_top, row_h):
            bb = draw.textbbox((0, 0), text, font=font)
            tx = cx - (bb[0] + bb[2]) // 2
            ty = y_top + (row_h - (bb[3] - bb[1])) // 2 - bb[1]
            draw.text((tx, ty), text, color, font=font)

        _draw_col_text(fc["day"],           font_day, BLACK, col_y0,                                 row_day_h)
        _draw_col_text(f"{fc['hi']}\u00b0", font_hi,  RED,   col_y0 + row_day_h + GAP,              row_hi_h)
        _draw_col_text(f"{fc['lo']}\u00b0", font_lo,  BLACK, col_y0 + row_day_h + GAP + row_hi_h + GAP // 2, row_lo_h)

    inky_display.set_image(img)
    inky_display.show()


if __name__ == "__main__":
    show()
