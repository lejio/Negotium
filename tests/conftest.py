"""Shared test fixtures for the Negotium test suite."""

from __future__ import annotations

import pytest

from negotium.config import (
    AppConfig,
    DiscordConfig,
    ExperienceLevel,
    LLMConfig,
    PostedWithin,
    SearchConfig,
)
from negotium.models.job import Job


# ─── Job fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def sample_job() -> Job:
    """A single realistic job listing."""
    return Job(
        title="Software Engineer",
        company="Acme Corp",
        location="San Francisco, CA",
        link="https://example.com/jobs/123",
        posted="2 hours ago",
        source="TestSource",
    )


@pytest.fixture
def sample_jobs() -> list[Job]:
    """A batch of job listings for testing."""
    return [
        Job(
            title="Software Engineer",
            company="Acme Corp",
            location="San Francisco, CA",
            link="https://example.com/jobs/1",
            posted="1 hour ago",
            source="LinkedIn",
        ),
        Job(
            title="Backend Developer",
            company="TechStart Inc",
            location="Remote",
            link="https://example.com/jobs/2",
            posted="3 hours ago",
            source="Indeed",
        ),
        Job(
            title="Full Stack Engineer",
            company="BigCo",
            location="New York, NY",
            link="https://example.com/jobs/3",
            posted="5 hours ago",
            source="LinkedIn",
        ),
    ]


# ─── Config fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def default_search_config() -> SearchConfig:
    return SearchConfig()


@pytest.fixture
def custom_search_config() -> SearchConfig:
    return SearchConfig(
        keywords="python developer",
        experience_levels=[ExperienceLevel.ENTRY_LEVEL, ExperienceLevel.ASSOCIATE],
        posted_within=PostedWithin.PAST_WEEK,
        location="Austin, TX",
        remote_only=True,
    )


@pytest.fixture
def discord_config() -> DiscordConfig:
    return DiscordConfig(
        webhook_url="https://discord.com/api/webhooks/test/token",
        username="Test Bot",
    )


@pytest.fixture
def disabled_discord_config() -> DiscordConfig:
    return DiscordConfig(webhook_url="")


@pytest.fixture
def llm_config(tmp_path) -> LLMConfig:
    resume = tmp_path / "resume.txt"
    resume.write_text("Experienced Python developer with 3 years of experience.")
    return LLMConfig(
        enabled=True,
        provider="openai",
        model="gpt-4o-mini",
        api_key="test-key",
        resume_path=resume,
        min_score_to_notify=50,
    )


@pytest.fixture
def disabled_llm_config() -> LLMConfig:
    return LLMConfig(enabled=False)


@pytest.fixture
def app_config(discord_config, llm_config) -> AppConfig:
    return AppConfig(
        check_interval_minutes=10,
        discord=discord_config,
        llm=llm_config,
    )
