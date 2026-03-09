"""Persistence layer for tracking previously seen job IDs."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "seen_jobs.json"


def load_seen_jobs(path: Path = DEFAULT_PATH) -> set[str]:
    """Load previously seen job IDs from disk."""
    if path.exists():
        with open(path, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_jobs(seen: set[str], path: Path = DEFAULT_PATH) -> None:
    """Persist seen job IDs to disk."""
    with open(path, "w") as f:
        json.dump(sorted(seen), f, indent=2)
