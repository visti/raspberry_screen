#!/usr/bin/env python3
"""Acceptance checks: render all screens to PNG against three fixtures.

Usage: python test_render.py
Output: /tmp/screen_*.png + pass/fail summary.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import word_display, sentence_display, romanian_display, refresh_display
from layout import save_preview, W, H, MARGIN, LEGEND_H, BLACK, WHITE, RED  # noqa: F401
from word_display import SENT_Y1 as WORD_SENT_Y1
from sentence_display import BOT_Y1 as SENT_BOT_Y1

FIXTURES = {
    "short": (
        ["mulighed",      "Det er en stor mulighed for dig."],
        ["opportunity",   "This is a great opportunity for you."],
        ["oportunitate",  "Aceasta este o mare oportunitate pentru tine."],
    ),
    "long": (
        ["sammenhængende",
         "Den sammenhængende fortælling gør det meget lettere for os alle at forstå tekstens budskab."],
        ["unambiguously",
         "The instructions were stated so unambiguously that every single member of the team could follow them."],
        ["neîndoielnic",
         "Instrucțiunile au fost formulate atât de neîndoielnic încât toți membrii echipei le-au înțeles."],
    ),
    "diacritic": (
        ["træ",   "Et gammelt egetræ med bøgekronen vokser i haven ved søen."],
        ["tree",  "An old oak tree with a beech crown grows in the garden by the lake."],
        ["șansă", "Aceasta este o șansă unică pentru a-ți arăta adevăratele abilități."],
    ),
}

# Content bottom boundary — nothing should render past this in margin zones
CONTENT_BOTTOM = min(WORD_SENT_Y1, SENT_BOT_Y1)   # 292


def _only_bwr(img_path):
    """Return list of non-BWR pixel coords (should be empty)."""
    from PIL import Image
    img = Image.open(img_path).convert("RGB")
    bad = []
    for y in range(H):
        for x in range(W):
            r, g, b = img.getpixel((x, y))
            if not (
                (r < 50  and g < 50  and b < 50)   or   # BLACK
                (r > 200 and g > 200 and b > 200)   or   # WHITE
                (r > 140 and g < 80  and b < 80)         # RED
            ):
                bad.append((x, y, r, g, b))
    return bad


def _margin_violations(img_path, skip_y_ranges=None):
    """BLACK pixels in x < MARGIN outside full-bleed regions (y >= LEGEND_H)."""
    from PIL import Image
    img  = Image.open(img_path).convert("RGB")
    skip = skip_y_ranges or []
    bad  = []
    for y in range(LEGEND_H, H):
        if any(lo <= y < hi for lo, hi in skip):
            continue
        for x in range(MARGIN):
            r, g, b = img.getpixel((x, y))
            if r < 50 and g < 50 and b < 50:
                bad.append((x, y))
    return bad


def _past_bottom(img_path, bottom_y):
    """Non-white pixels in x=MARGIN..W-MARGIN at y > bottom_y."""
    from PIL import Image
    img = Image.open(img_path).convert("RGB")
    bad = []
    for y in range(bottom_y + 1, H):
        for x in range(MARGIN, W - MARGIN):
            r, g, b = img.getpixel((x, y))
            if not (r > 200 and g > 200 and b > 200):
                bad.append((x, y))
    return bad


def _legend_consistent(imgs):
    """Check cell 3 (x 300-400, y 0-28) is pixel-identical across all screens.

    Cell 3 (E / NYT) is inactive in screens A, B, C.
    """
    from PIL import Image
    CELL3_X0, CELL3_X1 = 300, 400
    refs = [Image.open(p).convert("RGB").crop((CELL3_X0, 0, CELL3_X1, 28)) for p in imgs]
    diffs = []
    base  = refs[0]
    for other in refs[1:]:
        for xi in range(CELL3_X1 - CELL3_X0):
            for yi in range(28):
                if base.getpixel((xi, yi)) != other.getpixel((xi, yi)):
                    diffs.append((xi + CELL3_X0, yi))
    return diffs


def _check_truncation(prepared):
    """Verify no sentence line ends with the truncation ellipsis (…)."""
    from layout import fit_text, FONT_SG_REG
    from word_display import SENT_W, SENT_SIZES
    from sentence_display import INNER_W, SENT_SIZES as B_SENT_SIZES
    from PIL import Image, ImageDraw
    img  = Image.new("P", (W, H))
    draw = ImageDraw.Draw(img)

    dk, en, ro = prepared
    truncated  = []

    # Screen A sentences
    for text, sizes, box_w in [
        (dk[1], SENT_SIZES, SENT_W),
        (en[1], SENT_SIZES, SENT_W),
    ]:
        _, lines, _ = fit_text(draw, text, FONT_SG_REG, sizes, box_w, 1000, 1.24)
        for line in lines:
            if line.endswith("…"):
                truncated.append(f"A:{text[:40]}")

    # Screen B / C sentences
    for text, sizes, box_w in [
        (dk[1], B_SENT_SIZES, INNER_W),
        (en[1], B_SENT_SIZES, INNER_W),
        (ro[1], B_SENT_SIZES, INNER_W),
    ]:
        _, lines, _ = fit_text(draw, text, FONT_SG_REG, sizes, box_w, 1000, 1.22)
        for line in lines:
            if line.endswith("…"):
                truncated.append(f"B/C:{text[:40]}")

    return truncated


def run():
    results  = []
    all_imgs = []

    for name, (danish, english, romanian) in FIXTURES.items():
        prepared = (danish, english, romanian)

        for module, fname, skip_y in [
            (word_display,     f"screen_a_{name}.png",
             [(word_display.BAND_Y0, word_display.BAND_Y1)]),   # full-bleed BLACK band
            (sentence_display, f"screen_b_{name}.png", []),
            (romanian_display, f"screen_c_{name}.png", []),
        ]:
            img  = module.show(prepared)
            path = f"/tmp/{fname}"
            save_preview(img, path)
            all_imgs.append(path)

            bad_px   = _only_bwr(path)
            margin_v = _margin_violations(path, skip_y_ranges=skip_y)
            bottom_v = _past_bottom(path, CONTENT_BOTTOM)
            ok = not bad_px and not margin_v and not bottom_v
            results.append((fname, ok,
                             f"non-BWR:{len(bad_px)} margin:{len(margin_v)} past-bottom:{len(bottom_v)}"))
            print(f"{'✓' if ok else '✗'} {fname}  ({results[-1][2]})")

    # Screen E
    img  = refresh_display.show()
    path = "/tmp/screen_e.png"
    save_preview(img, path)
    all_imgs.append(path)
    bad_px = _only_bwr(path)
    ok = not bad_px
    results.append(("screen_e.png", ok, f"non-BWR:{len(bad_px)}"))
    print(f"{'✓' if ok else '✗'} screen_e.png  ({results[-1][2]})")

    # Legend consistency across A, B, C for the "short" fixture
    legend_imgs = [f"/tmp/screen_{s}_short.png" for s in ("a", "b", "c")]
    diffs = _legend_consistent(legend_imgs)
    lck   = not diffs
    print(f"{'✓' if lck else '✗'} legend consistent  (diff pixels: {len(diffs)})")

    # No truncation on long fixture
    trunc = _check_truncation(FIXTURES["long"])
    tck   = not trunc
    print(f"{'✓' if tck else '✗'} no truncation on long  ({'; '.join(trunc) if trunc else 'ok'})")

    total_ok = sum(1 for _, ok, _ in results) + lck + tck
    total    = len(results) + 2
    print(f"\n{total_ok}/{total} checks passed.")
    if total_ok < total:
        sys.exit(1)


if __name__ == "__main__":
    run()
