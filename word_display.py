"""word_display.py — Screen A (Button A): Layout 7b."""

import word_of_the_day
from PIL import ImageFont, ImageDraw
from layout import (
    FONT_JOST_MED, FONT_JOST_SEMI, FONT_SG_REG,
    MARGIN, LEGEND_H, W, H, BLACK, WHITE, RED,
    draw_tracked, fit_text, draw_lines, dither_rect, block_height,
    get_inky, make_canvas, save_preview, draw_legend,
)

# ── Black band geometry ────────────────────────────────────────────────────────
BAND_Y0    = LEGEND_H   # 31
BAND_Y1    = 127
BAND_PAD_H = 10
BAND_PAD_W = MARGIN     # 16
TEXT_W     = W - BAND_PAD_W * 2   # 368
AVAIL_H    = BAND_Y1 - BAND_Y0 - BAND_PAD_H * 2   # 76

# ── Sentence stack geometry ────────────────────────────────────────────────────
SENT_Y0    = 145
SENT_Y1    = 292
SENT_AVAIL = SENT_Y1 - SENT_Y0   # 147
SENT_W     = W - MARGIN * 2      # 368
GAP_LBL    = 4     # label → sentence gap
RULE_H     = 3
GAP_RULE   = 12    # sentence → rule gap and rule → label gap
LBL_SZ     = 11
SENT_SIZES = [16, 15, 14, 13]


def prepare():
    return word_of_the_day.get_word()


def show(prepared=None):
    danish, english, _romanian = (
        prepared if prepared is not None else word_of_the_day.get_word()
    )
    dk_word = danish[0]
    dk_sent = danish[1]
    en_word = english[0]
    en_sent = english[1]

    inky = get_inky()
    inky.set_border(inky.BLACK)
    img  = make_canvas(inky)
    draw = ImageDraw.Draw(img)

    # White ground + legend
    draw.rectangle((0, 0, W, H), WHITE)
    draw_legend(draw, 0)

    # ── Black band ─────────────────────────────────────────────────────────────
    draw.rectangle((0, BAND_Y0, W, BAND_Y1 - 1), BLACK)

    # English word — fit first so we know row_h for dk centering
    font_en, en_lines, en_lh = fit_text(
        draw, en_word.upper(), FONT_JOST_SEMI,
        [18, 16, 14], 320, AVAIL_H, line_ratio=1.0,
    )
    en_bh  = block_height(en_lines, font_en, en_lh)
    row_h  = max(4, en_bh)
    bar_h, bar_w, gap_bar = 4, 30, 10

    # Danish word — max 2 lines, box_h = remaining band space after row + gap
    dk_box_h = max(1, AVAIL_H - 8 - row_h)
    font_dk, dk_lines, dk_lh = fit_text(
        draw, dk_word.upper(), FONT_JOST_SEMI,
        [44, 40, 36, 32, 28], TEXT_W, dk_box_h, line_ratio=1.0,
    )
    dk_lines = dk_lines[:2]
    dk_bh   = block_height(dk_lines, font_dk, dk_lh)

    # Vertically centre the two blocks (+ 1px gap) in the available band height
    total_band = dk_bh + 1 + row_h
    cy = BAND_Y0 + BAND_PAD_H + max(0, (AVAIL_H - total_band) // 2)

    # Danish word — WHITE, left-aligned at x=16
    cy = draw_lines(draw, dk_lines, font_dk, WHITE,
                    MARGIN, cy, TEXT_W, dk_lh)
    cy += 1   # gap between dk block and row

    # Row: 30×4px RED bar + 10px gap + English word in RED
    row_y_bar = cy + (row_h - bar_h) // 2
    row_y_en  = cy + (row_h - en_bh) // 2
    draw.rectangle((MARGIN, row_y_bar, MARGIN + bar_w, row_y_bar + bar_h - 1), RED)
    draw_tracked(draw, (MARGIN + bar_w + gap_bar, row_y_en),
                 en_word.upper(), font_en, RED, 1.1)

    # ── RED divider y=127–131 ──────────────────────────────────────────────────
    draw.rectangle((0, BAND_Y1, W, BAND_Y1 + 4 - 1), RED)

    # ── Sentence stack — top-down from y=145 ──────────────────────────────────
    font_lbl = ImageFont.truetype(FONT_JOST_MED, LBL_SZ)
    lbl_h    = font_lbl.getmetrics()[0] + font_lbl.getmetrics()[1]

    font_dk_s, dk_s_lines, dk_s_lh = fit_text(
        draw, dk_sent, FONT_SG_REG, SENT_SIZES, SENT_W, SENT_AVAIL, line_ratio=1.24,
    )
    font_en_s, en_s_lines, en_s_lh = fit_text(
        draw, en_sent, FONT_SG_REG, SENT_SIZES, SENT_W, SENT_AVAIL, line_ratio=1.24,
    )
    gap_r = GAP_RULE

    def _stack_h(g):
        dk_h = block_height(dk_s_lines, font_dk_s, dk_s_lh)
        en_h = block_height(en_s_lines, font_en_s, en_s_lh)
        return lbl_h + GAP_LBL + dk_h + g + RULE_H + g + lbl_h + GAP_LBL + en_h

    # Step both sentences down together if stack is too tall
    if _stack_h(gap_r) > SENT_AVAIL:
        for sz in [15, 14, 13]:
            font_dk_s, dk_s_lines, dk_s_lh = fit_text(
                draw, dk_sent, FONT_SG_REG, [sz], SENT_W, SENT_AVAIL, line_ratio=1.24,
            )
            font_en_s, en_s_lines, en_s_lh = fit_text(
                draw, en_sent, FONT_SG_REG, [sz], SENT_W, SENT_AVAIL, line_ratio=1.24,
            )
            if _stack_h(gap_r) <= SENT_AVAIL:
                break

    # Reduce gaps to 8px if still over
    if _stack_h(gap_r) > SENT_AVAIL:
        gap_r = 8

    # Draw top-down
    ry = SENT_Y0
    draw_tracked(draw, (MARGIN, ry), "DANSK", font_lbl, RED, 2.2)
    ry += lbl_h + GAP_LBL

    ry = draw_lines(draw, dk_s_lines, font_dk_s, BLACK, MARGIN, ry, SENT_W, dk_s_lh)
    ry += gap_r

    dither_rect(img, (MARGIN, ry, W - MARGIN, ry + RULE_H), BLACK, WHITE, cell=3)
    ry += RULE_H + gap_r

    draw_tracked(draw, (MARGIN, ry), "ENGLISH", font_lbl, BLACK, 2.2)
    ry += lbl_h + GAP_LBL

    draw_lines(draw, en_s_lines, font_en_s, BLACK, MARGIN, ry, SENT_W, en_s_lh)

    inky.set_image(img)
    inky.show()
    return img


if __name__ == "__main__":
    img = show()
    save_preview(img, "/tmp/screen_a.png")
    print("Saved /tmp/screen_a.png")
