"""Cycles through full black/white refreshes to clear e-ink ghosting."""
from inky.auto import auto
from PIL import Image, ImageDraw

def clear(cycles=3):
    inky_display = auto()
    W, H = inky_display.WIDTH, inky_display.HEIGHT
    colors = [inky_display.WHITE, inky_display.BLACK] * cycles + [inky_display.WHITE]
    for i, color in enumerate(colors):
        print(f"  Refresh {i+1}/{len(colors)}...")
        img = Image.new("P", (W, H))
        ImageDraw.Draw(img).rectangle((0, 0, W, H), color)
        inky_display.set_image(img)
        inky_display.show()
    print("Done.")


def flash():
    """Clear including a red pass to reset the BWR red channel."""
    inky_display = auto()
    W, H = inky_display.WIDTH, inky_display.HEIGHT
    for color in [inky_display.RED, inky_display.BLACK, inky_display.WHITE]:
        img = Image.new("P", (W, H))
        ImageDraw.Draw(img).rectangle((0, 0, W, H), color)
        inky_display.set_image(img)
        inky_display.show()

if __name__ == '__main__':
    clear()
