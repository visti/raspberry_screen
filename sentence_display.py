"""sentence_display.py — Screen B (Button B): Layout 7b.

draw_split() is shared with romanian_display (Screen C).
"""

import word_of_the_day
from PIL import ImageFont, ImageDraw
from layout import (
    FONT_JOST_MED, FONT_JOST_SEMI, FONT_SG_REG,
    MARGIN, W, H, BLACK, WHITE, RED,
    draw_tracked, fit_text, draw_lines, dither_rect, block_height,
    get_inky, make_canvas, save_preview, draw_legend,
)

# ── Geometry ───────────────────────────────────────────────────────────────────
DIV_Y0, DIV_Y1  = 163, 167     # RED centre bar
TOP_Y0, TOP_Y1  = 39,  159     # top half content area
BOT_Y0, BOT_Y1  = 175, 292     # bottom half content area
INNER_W         = W - MARGIN * 2   # 368
LABEL_ROW_H     = 24
WORD_SZ         = 22
LBL_SZ          = 12
LBL_TRACKING    = 2.4
SENT_SIZES      = [24, 22, 20, 18, 16]


def prepare():
    return word_of_the_day.get_word()


def draw_split(draw, img, active_index,
               top_word, top_label, top_sentence, top_color,
               bot_word, bot_label, bot_sentence, bot_color,
               top_rule_cell=3, bot_rule_cell=4):
    """Shared layout engine for Screens B and C."""
    draw.rectangle((0, 0, W, H), WHITE)
    draw_legend(draw, active_index)

    # RED centre divider
    draw.rectangle((0, DIV_Y0, W, DIV_Y1 - 1), RED)

    font_word = ImageFont.truetype(FONT_JOST_SEMI, WORD_SZ)
    font_lbl  = ImageFont.truetype(FONT_JOST_MED,  LBL_SZ)

    for (y0, y1, word, label, sentence, wcolor, rule_cell) in [
        (TOP_Y0, TOP_Y1, top_word, top_label, top_sentence, top_color, top_rule_cell),
        (BOT_Y0, BOT_Y1, bot_word, bot_label, bot_sentence, bot_color, bot_rule_cell),
    ]:
        sent_avail = y1 - y0 - LABEL_ROW_H
        word_str   = word.upper()

        # Vertical centre of label row
        wh       = font_word.getmetrics()[0] + font_word.getmetrics()[1]
        lh       = font_lbl.getmetrics()[0]  + font_lbl.getmetrics()[1]
        row_mid  = y0 + LABEL_ROW_H // 2
        word_y   = row_mid - wh // 2
        label_y  = row_mid - lh // 2

        word_w   = draw.textlength(word_str, font=font_word)
        label_tw = (sum(draw.textlength(c, font=font_lbl) + LBL_TRACKING
                        for c in label) - LBL_TRACKING)

        draw.text((MARGIN, word_y), word_str, wcolor, font=font_word)
        draw_tracked(draw, (0, label_y), label, font_lbl, wcolor,
                     LBL_TRACKING, anchor_right=W - MARGIN)

        # Dither rule between word and label (10px clearance each side)
        rule_x0  = MARGIN + word_w + 10
        rule_x1  = W - MARGIN - label_tw - 10
        rule_mid = y0 + LABEL_ROW_H // 2
        if rule_x1 > rule_x0:
            dither_rect(img, (rule_x0, rule_mid - 1, rule_x1, rule_mid + 2),
                        wcolor, WHITE, cell=rule_cell)

        # Sentence — vertically centred in the area below the label row
        sent_area_top = y0 + LABEL_ROW_H
        font_sent, sent_lines, sent_lh = fit_text(
            draw, sentence, FONT_SG_REG, SENT_SIZES,
            INNER_W, sent_avail, line_ratio=1.22,
        )
        sent_bh = block_height(sent_lines, font_sent, sent_lh)
        sent_y  = sent_area_top + max(0, (y1 - sent_area_top - sent_bh) // 2)
        draw_lines(draw, sent_lines, font_sent, BLACK, MARGIN, sent_y,
                   INNER_W, sent_lh)


def show(prepared=None):
    danish, english, _romanian = (
        prepared if prepared is not None else word_of_the_day.get_word()
    )

    inky = get_inky()
    inky.set_border(inky.WHITE)
    img  = make_canvas(inky)
    draw = ImageDraw.Draw(img)

    draw_split(
        draw, img, active_index=1,
        top_word=danish[0],  top_label="DANSK",   top_sentence=danish[1],  top_color=RED,
        bot_word=english[0], bot_label="ENGLISH", bot_sentence=english[1], bot_color=BLACK,
        top_rule_cell=3, bot_rule_cell=4,
    )

    inky.set_image(img)
    inky.show()
    return img


if __name__ == "__main__":
    img = show()
    save_preview(img, "/tmp/screen_b.png")
    print("Saved /tmp/screen_b.png")
