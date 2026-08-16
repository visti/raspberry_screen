"""word_of_the_day.py — fetches a daily word via Gemini API with local caching.

Uses raw httpx (no SDK) to avoid Rust compile requirements on armv6 Pi.

Interface:
    danish, english, romanian = get_word()
    danish[0]   → Danish word        danish[1]   → Danish example sentence
    english[0]  → English word       english[1]  → English example sentence
    romanian[0] → Romanian word      romanian[1] → Romanian example sentence
"""

import json
import os
import random
import time
from datetime import date
from pathlib import Path

import httpx

CACHE_PATH    = Path.home() / ".cache" / "word_of_the_day.json"
HISTORY_PATH  = Path.home() / ".cache" / "word_history.json"
FALLBACK_PATH = Path(__file__).parent / "fallbacks.json"

_HISTORY_MAX = 10

_HARDCODED_FALLBACK = (
    ["Sommerfugl", "En sommerfugl flyver over blomsten."],
    ["Butterfly",  "A butterfly flies over the flower."],
    ["Fluture",    "Un fluture zboară peste floare."],
)


def get_history() -> list[str]:
    """Return the list of recent Danish words (newest last), up to _HISTORY_MAX."""
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _add_to_history(danish_word: str) -> None:
    history = get_history()
    # deduplicate: remove previous occurrence so word moves to tail
    history = [w for w in history if w.lower() != danish_word.lower()]
    history.append(danish_word)
    history = history[-_HISTORY_MAX:]
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _random_fallback(avoid_words: list[str] | None = None):
    """Return a random entry from fallbacks.json, or the hardcoded one.

    avoid_words: Danish words to exclude (case-insensitive).  If the pool
    shrinks to zero after filtering, the avoid constraint is dropped.
    """
    try:
        pool = json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))
        if pool:
            if avoid_words:
                lower_avoid = {w.lower() for w in avoid_words}
                filtered = [e for e in pool
                            if e["danish_word"].lower() not in lower_avoid]
                pool = filtered or pool  # never return nothing
            entry = random.choice(pool)
            return (
                [entry["danish_word"],   entry["danish_sentence"]],
                [entry["english_word"],  entry["english_sentence"]],
                [entry["romanian_word"], entry["romanian_sentence"]],
            )
    except Exception:
        pass
    return _HARDCODED_FALLBACK

_SCHEMA = {
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
}


def _load_cache() -> dict:
    try:
        with CACHE_PATH.open() as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(data: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clear_today() -> str | None:
    """Remove today's cache entry. Returns the cleared Danish word (or None)."""
    today = date.today().isoformat()
    cache = _load_cache()
    if today in cache:
        word = cache[today].get("danish_word")
        del cache[today]
        try:
            _save_cache(cache)
        except Exception:
            pass
        return word
    return None


_MODELS = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]
_MAX_RETRIES = 3
_RETRY_DELAY = 4   # seconds between retries


def _fetch_from_api(avoid_words: list[str] | None = None) -> dict:
    api_key = os.environ["GEMINI_API_KEY"]
    if avoid_words:
        quoted = ", ".join(f"'{w}'" for w in avoid_words)
        avoid_clause = f" Do NOT pick any of these words: {quoted} — choose a completely different word."
    else:
        avoid_clause = ""
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Pick a Danish word of the day for a language learner. "
                            "Choose a common, practical Danish word — the kind that "
                            "appears frequently in everyday speech and writing "
                            "(e.g. verbs like 'fortælle', 'betyde', 'hjælpe', "
                            "adjectives like 'rolig', 'glad', 'travl', "
                            "nouns like 'forskel', 'sted', 'tid'). "
                            "Avoid rare, archaic, or highly specialised words."
                            + avoid_clause +
                            " Provide the Danish word and a natural Danish example "
                            "sentence, its English translation with a natural English "
                            "example sentence, and its Romanian translation with a "
                            "natural Romanian example sentence."
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema":   _SCHEMA,
        },
    }
    for model in _MODELS:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        for attempt in range(_MAX_RETRIES):
            try:
                response = httpx.post(
                    url,
                    headers={"X-goog-api-key": api_key},
                    json=payload,
                    timeout=60.0,
                )
                response.raise_for_status()
                text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
            except Exception:
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_DELAY)
    raise RuntimeError(f"All models failed after {_MAX_RETRIES} attempts each")


def get_word(avoid_words: list[str] | None = None):
    """Return ([danish_word, danish_sentence], [english_word, english_sentence],
               [romanian_word, romanian_sentence]).

    avoid_words: list of Danish words to exclude (passed to API + fallback picker).
    """
    today = date.today().isoformat()
    cache = _load_cache()

    if today in cache:
        entry = cache[today]
        return (
            [entry["danish_word"],   entry["danish_sentence"]],
            [entry["english_word"],  entry["english_sentence"]],
            [entry.get("romanian_word",    _HARDCODED_FALLBACK[2][0]),
             entry.get("romanian_sentence", _HARDCODED_FALLBACK[2][1])],
        )

    try:
        word = _fetch_from_api(avoid_words=avoid_words)
    except Exception:
        # Cache the fallback so A, B, C all show the same word today
        fallback = _random_fallback(avoid_words=avoid_words)
        try:
            cache[today] = {
                "danish_word":      fallback[0][0], "danish_sentence":  fallback[0][1],
                "english_word":     fallback[1][0], "english_sentence": fallback[1][1],
                "romanian_word":    fallback[2][0], "romanian_sentence":fallback[2][1],
            }
            _save_cache(cache)
        except Exception:
            pass
        _add_to_history(fallback[0][0])
        return fallback

    try:
        cache[today] = word
        _save_cache(cache)
    except Exception:
        pass
    _add_to_history(word["danish_word"])

    return (
        [word["danish_word"],   word["danish_sentence"]],
        [word["english_word"],  word["english_sentence"]],
        [word["romanian_word"], word["romanian_sentence"]],
    )
