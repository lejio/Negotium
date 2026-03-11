"""
Centralized configuration for Negotium.

All user-facing knobs live here — search preferences, notification
settings, LLM config, etc.  Import this module anywhere you need them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


# ─── Experience Level ────────────────────────────────────────────────────────


class ExperienceLevel(Enum):
    """
    LinkedIn experience-level filter values.

    These map directly to LinkedIn's ``f_E`` query parameter.
    Multiple levels can be combined: ``"1,2"`` = internship + entry-level.
    """

    INTERNSHIP = "1"
    ENTRY_LEVEL = "2"
    ASSOCIATE = "3"
    MID_SENIOR = "4"
    DIRECTOR = "5"
    EXECUTIVE = "6"


# ─── Time Filter ─────────────────────────────────────────────────────────────


class PostedWithin(Enum):
    """LinkedIn ``f_TPR`` time-range values."""

    PAST_HOUR = "r3600"
    PAST_24H = "r86400"
    PAST_WEEK = "r604800"
    PAST_MONTH = "r2592000"


# ─── Search Config ───────────────────────────────────────────────────────────


@dataclass
class SearchConfig:
    """
    Encapsulates all search preferences for a query.

    Used by sources to build platform-specific filters from a
    single, platform-agnostic configuration object.
    """

    keywords: str = "software engineer"
    experience_levels: list[ExperienceLevel] = field(
        default_factory=lambda: [ExperienceLevel.ENTRY_LEVEL],
    )
    posted_within: PostedWithin = PostedWithin.PAST_24H
    location: str = ""  # free-text, e.g. "San Francisco, CA"
    remote_only: bool = False

    # ── helpers ───────────────────────────────────────────────────────

    @property
    def experience_filter_value(self) -> str:
        """Comma-joined level codes for LinkedIn's ``f_E`` param."""
        return ",".join(lvl.value for lvl in self.experience_levels)


# ─── Discord Config ──────────────────────────────────────────────────────────


@dataclass
class DiscordConfig:
    """
    Settings for the Discord webhook notifier.

    Set ``webhook_url`` to a Discord channel webhook URL to enable.
    Leave empty to disable Discord notifications.
    """

    webhook_url: str = ""  # Discord channel webhook URL
    username: str = "Negotium Bot"
    avatar_url: str = ""


# ─── LLM Config ──────────────────────────────────────────────────────────────


@dataclass
class LLMConfig:
    """
    Settings for the LLM-based job ranking feature.

    Set ``enabled = True`` and provide an ``api_key`` + ``resume_path``
    to activate ranking.  Each new job will be scored 0-100 based on
    how well it matches your resume / profile.

    Providers:
        - ``"openai"``  — OpenAI API (requires ``api_key``)
        - ``"local"``   — Any OpenAI-compatible local server
                          (Ollama, LM Studio, llama.cpp, vLLM, etc.)
                          Set ``base_url`` to the server endpoint.
    """

    enabled: bool = False
    provider: str = "openai"  # "openai" | "local"
    model: str = "gpt-4o-mini"
    api_key: str = ""  # or set OPENAI_API_KEY env var
    base_url: str = "http://localhost:11434/v1"  # local server URL (Ollama default)
    resume_path: Path = Path("resume.txt")
    min_score_to_notify: int = 0  # only notify for jobs scoring >= this


# ─── Firecrawl Config ────────────────────────────────────────────────────────


@dataclass
class FirecrawlConfig:
    """Settings for the self-hosted Firecrawl scraping API.

    When ``enabled`` is *True*, sources that support Firecrawl will
    fetch pages through the Firecrawl API (Playwright-based rendering)
    instead of launching a local Selenium / Chrome process.
    """

    enabled: bool = False
    api_url: str = "http://localhost:3002"


# ─── App Config ──────────────────────────────────────────────────────────────


@dataclass
class AppConfig:
    """Top-level application configuration."""

    check_interval_minutes: int = 15
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    firecrawl: FirecrawlConfig = field(default_factory=FirecrawlConfig)
