#!/usr/bin/env python3
"""
Button daemon — clears the display on startup then listens for button presses.

Display is unflipped, so A is the leftmost button and E is the rightmost.
buttonshim labels are reversed from the PCB silk-screen after the orientation
change, so we remap them at import time.

  Button A (leftmost)  → Word of the Day
  Button B (2nd)       → Sentences (today's word in context)
  Button C (middle)    → Romanian definition
  Button D             → (physically broken)
  Button E (rightmost) → Fetch a fresh word of the day (clears cache)
"""

import signal
import threading
import traceback

import buttonshim
import clear_display
import word_display
import word_of_the_day
import sentence_display
import romanian_display
import refresh_display

def _safe_fallback(avoid_words=None):
    """Return a guaranteed-available prepared tuple (never triggers a network call)."""
    try:
        return word_of_the_day._random_fallback(avoid_words=avoid_words)
    except Exception:
        return (
            ["Sommerfugl", "En sommerfugl flyver over blomsten."],
            ["Butterfly",  "A butterfly flies over the flower."],
            ["Fluture",    "Un fluture zboară peste floare."],
        )

# buttonshim names the leftmost button E and rightmost A because the PCB was
# designed for the opposite orientation.  Remap so our code uses intuitive
# left-to-right A→E order.
BUTTON_A = buttonshim.BUTTON_E
BUTTON_B = buttonshim.BUTTON_D
BUTTON_C = buttonshim.BUTTON_C
BUTTON_D = buttonshim.BUTTON_B
BUTTON_E = buttonshim.BUTTON_A

_lock = threading.Lock()

_PREPARE_TIMEOUT = 30   # seconds; prevents API stall from hogging the lock


def _run(fn, led_rgb, prepare=None):
    """Acquire lock, flash clear, run fn, clear LED.

    If prepare is given it is called in a background thread concurrently
    with clear_display.flash() so the API fetch overlaps the slow e-ink
    refresh.  fn is then called with the prepared data as its only argument
    (None on timeout — fn falls back to static data).
    Without prepare, fn is called with no arguments (existing behaviour).
    """
    if not _lock.acquire(blocking=False):
        print("Lock busy, ignoring press", flush=True)
        return
    try:
        print(f"Running {fn.__name__}", flush=True)
        buttonshim.set_pixel(*led_rgb)

        if prepare is not None:
            prep_result = [None]
            def _do_prepare():
                try:
                    prep_result[0] = prepare()
                except Exception:
                    pass  # fn will fall back to static data when it receives None
            prep_thread = threading.Thread(target=_do_prepare, daemon=True)
            prep_thread.start()
            clear_display.flash()
            prep_thread.join(timeout=_PREPARE_TIMEOUT)
            # If prepare timed out, use a local fallback — never re-trigger a network call
            fn(prep_result[0] if prep_result[0] is not None else _safe_fallback())
        else:
            clear_display.flash()
            fn()

        print(f"Done {fn.__name__}", flush=True)
    except Exception:
        traceback.print_exc()
    finally:
        buttonshim.set_pixel(0, 0, 0)
        _lock.release()


@buttonshim.on_press(BUTTON_A)
def button_a(button, pressed):
    threading.Thread(
        target=_run, args=(word_display.show, (0, 0, 255)),
        kwargs={"prepare": word_display.prepare}, daemon=True,
    ).start()


@buttonshim.on_press(BUTTON_B)
def button_b(button, pressed):
    threading.Thread(
        target=_run, args=(sentence_display.show, (0, 255, 0)),
        kwargs={"prepare": sentence_display.prepare}, daemon=True,
    ).start()


@buttonshim.on_press(BUTTON_C)
def button_c(button, pressed):
    threading.Thread(
        target=_run, args=(romanian_display.show, (255, 100, 0)),
        kwargs={"prepare": romanian_display.prepare}, daemon=True,
    ).start()


def _run_refresh():
    """Button E: show interstitial immediately, then fetch + display fresh word."""
    if not _lock.acquire(blocking=False):
        print("Lock busy, ignoring press", flush=True)
        return
    try:
        buttonshim.set_pixel(255, 0, 255)
        # Push interstitial right away — gives user feedback during panel refresh
        refresh_display.show()
        # Build avoid list: history (last 10) + today's word being replaced
        history = word_of_the_day.get_history()
        old_word = word_of_the_day.clear_today()
        if old_word and (not history or history[-1].lower() != old_word.lower()):
            history = history + [old_word]
        avoid_words = history[-10:] if history else None
        prepared = word_of_the_day.get_word(avoid_words=avoid_words)
        word_display.show(prepared)
        print("Done refresh", flush=True)
    except Exception:
        traceback.print_exc()
    finally:
        buttonshim.set_pixel(0, 0, 0)
        _lock.release()


@buttonshim.on_press(BUTTON_E)
def button_e(button, pressed):
    threading.Thread(target=_run_refresh, daemon=True).start()


if __name__ == '__main__':
    print("Clearing display...")
    buttonshim.set_pixel(255, 50, 0)   # orange = clearing
    clear_display.clear(cycles=3)
    buttonshim.set_pixel(0, 0, 0)

    print("Ready — A: word  |  B: sentences  |  C: romanian  |  E: new word")
    signal.pause()
