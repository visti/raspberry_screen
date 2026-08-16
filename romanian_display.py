"""romanian_display.py — Screen C (Button C): Layout 7b."""

import word_of_the_day
from PIL import ImageDraw
from layout import get_inky, make_canvas, save_preview
from sentence_display import draw_split

RED, BLACK = 2, 0


def prepare():
    return word_of_the_day.get_word()


def show(prepared=None):
    danish, _english, romanian = (
        prepared if prepared is not None else word_of_the_day.get_word()
    )

    inky = get_inky()
    inky.set_border(inky.WHITE)
    img  = make_canvas(inky)
    draw = ImageDraw.Draw(img)

    draw_split(
        draw, img, active_index=2,
        top_word=romanian[0], top_label="ROMÂNĂ",  top_sentence=romanian[1], top_color=RED,
        bot_word=danish[0],   bot_label="DANSK",   bot_sentence=danish[1],   bot_color=BLACK,
        top_rule_cell=3, bot_rule_cell=4,
    )

    inky.set_image(img)
    inky.show()
    return img


if __name__ == "__main__":
    img = show()
    save_preview(img, "/tmp/screen_c.png")
    print("Saved /tmp/screen_c.png")
