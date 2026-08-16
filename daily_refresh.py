#!/usr/bin/env python3
"""daily_refresh.py — run at 6am by inky-daily.timer.

1. Clears today's cached word so a fresh one gets fetched.
2. Pre-fetches the new word (warms cache before anyone presses A).
3. Runs generate_fallbacks.py --add 20 to slowly grow the fallback pool.
"""

import subprocess
import sys
from pathlib import Path

import word_of_the_day

HERE = Path(__file__).parent


def main():
    # 1. Clear + pre-fetch today's word
    print("Clearing today's cache…", flush=True)
    word_of_the_day.clear_today()

    print("Pre-fetching new word of the day…", flush=True)
    try:
        dk, en, _ = word_of_the_day.get_word()
        print(f"Word: {dk[0]} / {en[0]}", flush=True)
    except Exception as exc:
        print(f"Word fetch failed: {exc}", flush=True)

    # 2. Grow fallback pool by 20 words
    print("Growing fallback pool (+20 words)…", flush=True)
    result = subprocess.run(
        [sys.executable, str(HERE / "generate_fallbacks.py"), "--add", "20"],
        cwd=str(HERE),
    )
    if result.returncode != 0:
        print("Fallback generation failed (quota likely exhausted — will retry tomorrow)", flush=True)

    print("Daily refresh done.", flush=True)


if __name__ == "__main__":
    main()
