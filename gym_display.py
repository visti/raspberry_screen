import calendar
from datetime import date

import gym_tracker
from inky.auto import auto
from PIL import Image, ImageFont, ImageDraw

FONT_HEADER = "/home/visti/.fonts/Bebas.ttf"
FONT_BODY   = "/home/visti/.fonts/Yantramanav-Regular.ttf"

MARGIN = 16
GAP    = 6


def show():
    today    = date.today()
    gym_days = gym_tracker.get_gym_days(today.year, today.month)

    inky_display = auto()
    inky_display.set_border(inky_display.WHITE)
    W, H = inky_display.WIDTH, inky_display.HEIGHT

    img  = Image.new("P", (W, H))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, H), inky_display.WHITE)

    # ── month/year header ─────────────────────────────────────────────────────
    header_str  = today.strftime("%B %Y").upper()
    font_header = ImageFont.truetype(FONT_HEADER, 52)
    bb_h        = draw.textbbox((0, 0), header_str, font=font_header)
    header_h    = bb_h[3] - bb_h[1]
    draw.text(((W - (bb_h[2] - bb_h[0])) // 2, MARGIN),
              header_str, inky_display.RED, font=font_header)

    divider_y = MARGIN + header_h + GAP
    draw.rectangle((MARGIN, divider_y, W - MARGIN, divider_y + 2), inky_display.RED)

    # ── day-name row ──────────────────────────────────────────────────────────
    font_dayname = ImageFont.truetype(FONT_BODY, 17)
    day_names    = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    cell_w       = (W - MARGIN * 2) // 7
    names_y      = divider_y + GAP * 2

    for i, name in enumerate(day_names):
        bb = draw.textbbox((0, 0), name, font=font_dayname)
        x  = MARGIN + i * cell_w + (cell_w - (bb[2] - bb[0])) // 2
        draw.text((x, names_y), name, inky_display.BLACK, font=font_dayname)

    bb_name     = draw.textbbox((0, 0), "Mo", font=font_dayname)
    names_h     = bb_name[3] - bb_name[1]
    grid_top    = names_y + names_h + GAP * 2

    # ── calendar grid ─────────────────────────────────────────────────────────
    weeks  = calendar.monthcalendar(today.year, today.month)  # Mon=0
    cell_h = (H - grid_top - MARGIN) // len(weeks)

    font_day = ImageFont.truetype(FONT_BODY, 20)
    font_x   = ImageFont.truetype(FONT_HEADER, 28)

    for week_i, week in enumerate(weeks):
        for day_i, day in enumerate(week):
            if day == 0:
                continue

            cx = MARGIN + day_i * cell_w + cell_w // 2
            cy = grid_top + week_i * cell_h + cell_h // 2

            is_today = (day == today.day)

            # Today: filled red circle
            if is_today:
                r = min(cell_w, cell_h) // 2 - 2
                draw.ellipse((cx - r, cy - r, cx + r, cy + r),
                             fill=inky_display.RED)

            if day in gym_days:
                # Gym day: show only X, visually centered in the cell
                x_str   = "X"
                bb_x    = draw.textbbox((0, 0), x_str, font=font_x)
                x_color = inky_display.WHITE if is_today else inky_display.RED
                draw.text((cx - (bb_x[0] + bb_x[2]) // 2,
                           cy - (bb_x[1] + bb_x[3]) // 2),
                          x_str, x_color, font=font_x)
            else:
                # Normal day: show number, visually centered in the cell
                day_str   = str(day)
                bb_day    = draw.textbbox((0, 0), day_str, font=font_day)
                day_color = inky_display.WHITE if is_today else inky_display.BLACK
                draw.text((cx - (bb_day[0] + bb_day[2]) // 2,
                           cy - (bb_day[1] + bb_day[3]) // 2),
                          day_str, day_color, font=font_day)

    inky_display.set_image(img)
    inky_display.show()


if __name__ == "__main__":
    show()
