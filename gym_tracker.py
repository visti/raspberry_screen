"""Persistent gym-day storage — a JSON list of ISO date strings."""
import json
import os
from datetime import date

DATA_FILE = os.path.expanduser("~/gym_tracker.json")


def _load():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE) as f:
        return json.load(f)


def _save(dates):
    with open(DATA_FILE, "w") as f:
        json.dump(sorted(set(dates)), f)


def toggle_today():
    """Toggle today. Returns True if now marked, False if now unmarked."""
    today = date.today().isoformat()
    dates = _load()
    if today in dates:
        dates.remove(today)
        _save(dates)
        return False
    else:
        dates.append(today)
        _save(dates)
        return True


def get_gym_days(year, month):
    """Return a set of day-of-month integers that are gym days in the given month."""
    prefix = f"{year:04d}-{month:02d}-"
    return {int(d[8:10]) for d in _load() if d.startswith(prefix)}
