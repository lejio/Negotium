"""Unified job listing model used across all sources."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class Job:
    """A single job listing, normalized across all platforms."""

    title: str
    company: str
    location: str
    link: str
    posted: str                          # human-readable time string
    source: str = ""                     # e.g. "LinkedIn", "Workday:Apple"
    job_id: str = field(default="", repr=False)
    match_score: int | None = None       # LLM-assigned 0-100 relevance score

    def __post_init__(self) -> None:
        if not self.job_id and self.link:
            self.job_id = hashlib.md5(self.link.encode()).hexdigest()
