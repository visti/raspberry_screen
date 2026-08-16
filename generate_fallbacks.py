#!/usr/bin/env python3
"""Generate / extend fallbacks.json with common Danish words.

Each run adds ADD_PER_RUN new words to whatever is already in the file.
Run whenever you want to grow the fallback pool:

    python generate_fallbacks.py          # adds 200 new words
    python generate_fallbacks.py --add 50 # adds 50 new words

Saves to fallbacks.json in the same directory.  Words already in the file
are never repeated.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

OUT = Path(__file__).parent / "fallbacks.json"
ADD_PER_RUN = 200
BATCH = 20
RETRY_DELAY = 8     # seconds between retries on error
RATE_DELAY  = 90    # seconds to wait on 429 before retrying
BATCH_DELAY = 8     # seconds between successful batches
MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest"]
MAX_CONSECUTIVE_FAILURES = 5   # give up and tell user to retry later

_BATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "words": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "danish_word":      {"type": "string"},
                    "danish_sentence":  {"type": "string"},
                    "english_word":     {"type": "string"},
                    "english_sentence": {"type": "string"},
                    "romanian_word":    {"type": "string"},
                    "romanian_sentence":{"type": "string"},
                },
                "required": [
                    "danish_word", "danish_sentence",
                    "english_word", "english_sentence",
                    "romanian_word", "romanian_sentence",
                ],
            },
        }
    },
    "required": ["words"],
}


def _load_existing():
    if OUT.exists():
        try:
            return json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save(entries):
    OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_batch(api_key, already_have):
    avoid = ", ".join(already_have[-60:]) if already_have else "none yet"
    prompt = (
        f"Generate exactly {BATCH} common, practical Danish words for a language "
        f"learner. Each should appear frequently in everyday Danish speech or writing. "
        f"Cover a mix of verbs, adjectives, and nouns across different topics "
        f"(emotions, work, nature, home, food, time, etc). "
        f"Do NOT repeat any of these already-generated words: {avoid}. "
        f"For each word provide: the Danish word, a natural Danish example sentence, "
        f"its English translation with a natural English example sentence, and its "
        f"Romanian translation with a natural Romanian example sentence."
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": _BATCH_SCHEMA,
        },
    }
    for model in MODELS:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        for attempt in range(2):
            try:
                r = httpx.post(
                    url,
                    headers={"X-goog-api-key": api_key},
                    json=payload,
                    timeout=90.0,
                )
                if r.status_code == 429:
                    print(f"  [{model}] rate limited — waiting {RATE_DELAY}s", flush=True)
                    time.sleep(RATE_DELAY)
                    continue
                r.raise_for_status()
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)["words"]
            except Exception as exc:
                print(f"  [{model}] attempt {attempt+1} failed: {exc}", flush=True)
                if attempt < 1:
                    time.sleep(RETRY_DELAY)
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--add", type=int, default=ADD_PER_RUN,
                        help=f"words to add this run (default {ADD_PER_RUN})")
    args = parser.parse_args()
    want = args.add

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY not set")

    entries = _load_existing()
    start_count = len(entries)
    goal = start_count + want
    print(f"Existing: {start_count} — adding {want} more → target {goal}", flush=True)

    added = 0
    fail_wait = 30        # seconds; doubles on consecutive failures, caps at 600
    consecutive_fails = 0
    while added < want:
        already_words = [e["danish_word"].lower() for e in entries]
        print(f"Fetching batch… ({added}/{want} added so far)", flush=True)

        batch = _fetch_batch(api_key, already_words)
        if not batch:
            consecutive_fails += 1
            if consecutive_fails >= MAX_CONSECUTIVE_FAILURES:
                print(
                    f"\nQuota likely exhausted after {consecutive_fails} consecutive "
                    f"failures. {len(entries)} words saved. Re-run tomorrow to continue.",
                    flush=True,
                )
                sys.exit(0)
            print(f"Batch failed ({consecutive_fails}/{MAX_CONSECUTIVE_FAILURES}), waiting {fail_wait}s…", flush=True)
            time.sleep(fail_wait)
            fail_wait = min(fail_wait * 2, 600)
            continue

        consecutive_fails = 0
        fail_wait = 30   # reset on success
        new = [
            w for w in batch
            if w["danish_word"].lower() not in already_words
        ]
        entries.extend(new)
        added += len(new)
        _save(entries)
        print(f"  +{len(new)} words → {len(entries)} total ({added}/{want} added)", flush=True)
        time.sleep(BATCH_DELAY)

    print(f"\nDone — {len(entries)} words in {OUT} (+{added} this run)", flush=True)


if __name__ == "__main__":
    main()
