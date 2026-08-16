"""refresh_display.py — Screen E interstitial (Button E): Layout 7b.

Pushed immediately on press so the user gets feedback while the panel
refreshes and Gemini fetches the new word.
"""

from PIL import ImageFont, ImageDraw
from layout import (
    FONT_JOST_MED, FONT_JOST_SEMI, FONT_SG_REG,
    MARGIN, LEGEND_H, W, H, BLACK, WHITE, RED,
    draw_tracked, fit_text, draw_lines, dither_rect,
    get_inky, make_canvas, save_preview, draw_legend,
)

RED_BLOCK_Y1 = 115


def show(step=None, total_steps=None):
    """Draw and push the interstitial. Returns the image."""
    inky = get_inky()
    inky.set_border(inky.WHITE)
    img  = make_canvas(inky)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, W, H), WHITE)
    draw_legend(draw, 3)

    # ── RED block y=31–115 ────────────────────────────────────────────────────
    draw.rectangle((0, LEGEND_H, W, RED_BLOCK_Y1 - 1), RED)

    font_title = ImageFont.truetype(FONT_JOST_SEMI, 44)
    font_badge = ImageFont.truetype(FONT_JOST_MED,  12)

    # "NYT ORD" — text bottom 14px above y=115
    ta, td = font_title.getmetrics()
    title_y = RED_BLOCK_Y1 - 14 - (ta + td)
    draw.text((MARGIN, max(LEGEND_H, title_y)), "NYT ORD", WHITE, font=font_title)

    # "E · REFRESH" — right-aligned to x=384, 12px below block top
    draw_tracked(draw, (0, LEGEND_H + 12), "E · REFRESH",
                 font_badge, WHITE, 1.7, anchor_right=W - MARGIN)

    # ── Danish message y=136 ──────────────────────────────────────────────────
    font_dk_msg, dk_lines, dk_lh = fit_text(
        draw, "Dagens ord er slettet. Henter et nyt…",
        FONT_SG_REG, [20, 17, 14], W - MARGIN * 2, 52, line_ratio=1.24,
    )
    y = 136
    y = draw_lines(draw, dk_lines, font_dk_msg, BLACK, MARGIN, y,
                   W - MARGIN * 2, dk_lh)

    # English message 12px below
    font_en_msg = ImageFont.truetype(FONT_SG_REG, 14)
    draw.text((MARGIN, y + 12), "Cache cleared. Fetching a new word.",
              BLACK, font=font_en_msg)

    # ── Progress bar y=224–242 (3px outline) ─────────────────────────────────
    bar_x0, bar_x1 = MARGIN, W - MARGIN
    bar_y0, bar_y1 = 224, 242
    inner_w = bar_x1 - bar_x0 - 6   # minus 3px border each side

    fraction = (step / total_steps) if (step and total_steps) else 0.62
    fill_w   = int(inner_w * fraction)

    draw.rectangle((bar_x0, bar_y0, bar_x1, bar_y1), WHITE)
    draw.rectangle((bar_x0, bar_y0,     bar_x1, bar_y0 + 3), BLACK)    # top
    draw.rectangle((bar_x0, bar_y1 - 3, bar_x1, bar_y1),     BLACK)    # bottom
    draw.rectangle((bar_x0, bar_y0, bar_x0 + 3, bar_y1),     BLACK)    # left
    draw.rectangle((bar_x1 - 3, bar_y0, bar_x1, bar_y1),     BLACK)    # right

    if fill_w > 0:
        dither_rect(img,
                    (bar_x0 + 3, bar_y0 + 3,
                     bar_x0 + 3 + fill_w, bar_y1 - 3),
                    BLACK, WHITE, cell=4)

    # ── Footer — text bottom at y=288 ────────────────────────────────────────
    skr_str   = "SKÆRMEN OPDATERES OM ET ØJEBLIK"
    font_foot = ImageFont.truetype(FONT_JOST_MED, 12)

    # Drop to 11px if text would exceed 300px
    if draw.textlength(skr_str, font=font_foot) > 300:
        font_foot = ImageFont.truetype(FONT_JOST_MED, 11)

    foot_h   = font_foot.getmetrics()[0] + font_foot.getmetrics()[1]
    footer_y = 288 - foot_h

    draw_tracked(draw, (MARGIN, footer_y), skr_str,   font_foot, BLACK, 1.9)
    draw_tracked(draw, (0, footer_y),      "2 / 3",   font_foot, RED,   0,
                 anchor_right=W - MARGIN)

    inky.set_image(img)
    inky.show()
    return img


if __name__ == "__main__":
    img = show()
    save_preview(img, "/tmp/screen_e.png")
    print("Saved /tmp/screen_e.png")
