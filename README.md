# raspberry_screen

E-ink word-of-the-day display for Raspberry Pi + Pimoroni Inky 400×300 (BWR).

Four buttons cycle through screens:

| Button | Screen | Content |
|--------|--------|---------|
| A | Word | Danish word + English translation, full layout |
| B | Sentences | Word in context, Danish / English split |
| C | Romanian | Romanian / Danish split |
| E | Refresh | Fetch a new word of the day |

## Hardware

- Raspberry Pi (any model with GPIO)
- [Pimoroni Inky Impression 4"](https://shop.pimoroni.com/products/inky-impression-4) — 400×300 BWR e-ink
- [Pimoroni Button SHIM](https://shop.pimoroni.com/products/button-shim)

## Setup

```bash
python -m venv inky-env
source inky-env/bin/activate
pip install pillow httpx inky[rpi] buttonshim
```

Copy all files to `~/` on the Pi, then install the systemd units:

```bash
# Edit GEMINI_API_KEY in both service files first
sudo cp systemd/inky.service systemd/inky-daily.service systemd/inky-daily.timer \
     /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now inky
sudo systemctl enable --now inky-daily.timer
```

## Daily refresh

`inky-daily.timer` fires at 06:00 every day: clears the word cache, pre-fetches
a new word, and adds 20 entries to the fallback pool.

## Fallback pool

When the Gemini API is unavailable the display picks a random word from
`fallbacks.json`. Grow the pool manually:

```bash
GEMINI_API_KEY=... python generate_fallbacks.py        # adds 200 words
GEMINI_API_KEY=... python generate_fallbacks.py --add 50
```

## Fonts

- [Jost](https://fonts.google.com/specimen/Jost) — SemiBold + Medium
- [Space Grotesk](https://fonts.google.com/specimen/Space+Grotesk) — Regular

Place `.ttf` files in `assets/fonts/`.
