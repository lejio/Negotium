"""Tests for negotium.config — configuration dataclasses and enums."""

from __future__ import annotations


from negotium.config import (
    AppConfig,
    DiscordConfig,
    ExperienceLevel,
    FirecrawlConfig,
    LLMConfig,
    PostedWithin,
)


class TestExperienceLevel:
    """Verify enum values map to LinkedIn's f_E parameters."""

    def test_values(self):
        assert ExperienceLevel.INTERNSHIP.value == "1"
        assert ExperienceLevel.ENTRY_LEVEL.value == "2"
        assert ExperienceLevel.ASSOCIATE.value == "3"
        assert ExperienceLevel.MID_SENIOR.value == "4"
        assert ExperienceLevel.DIRECTOR.value == "5"
        assert ExperienceLevel.EXECUTIVE.value == "6"

    def test_all_members(self):
        assert len(ExperienceLevel) == 6


class TestPostedWithin:
    """Verify time-range enum values."""

    def test_values(self):
        assert PostedWithin.PAST_HOUR.value == "r3600"
        assert PostedWithin.PAST_24H.value == "r86400"
        assert PostedWithin.PAST_WEEK.value == "r604800"
        assert PostedWithin.PAST_MONTH.value == "r2592000"

    def test_all_members(self):
        assert len(PostedWithin) == 4


class TestSearchConfig:
    """Test SearchConfig defaults and helpers."""

    def test_defaults(self, default_search_config):
        cfg = default_search_config
        assert cfg.keywords == "software engineer"
        assert cfg.experience_levels == [ExperienceLevel.ENTRY_LEVEL]
        assert cfg.posted_within == PostedWithin.PAST_24H
        assert cfg.location == ""
        assert cfg.remote_only is False

    def test_experience_filter_single(self, default_search_config):
        assert default_search_config.experience_filter_value == "2"

    def test_experience_filter_multiple(self, custom_search_config):
        # ENTRY_LEVEL=2, ASSOCIATE=3
        assert custom_search_config.experience_filter_value == "2,3"

    def test_custom_values(self, custom_search_config):
        cfg = custom_search_config
        assert cfg.keywords == "python developer"
        assert cfg.location == "Austin, TX"
        assert cfg.remote_only is True
        assert cfg.posted_within == PostedWithin.PAST_WEEK


class TestDiscordConfig:
    """Test Discord configuration defaults."""

    def test_defaults(self):
        cfg = DiscordConfig()
        assert cfg.webhook_url == ""
        assert cfg.username == "Negotium Bot"
        assert cfg.avatar_url == ""

    def test_is_disabled_when_empty(self, disabled_discord_config):
        assert disabled_discord_config.webhook_url == ""

    def test_custom(self, discord_config):
        assert "discord.com" in discord_config.webhook_url
        assert discord_config.username == "Test Bot"


class TestLLMConfig:
    """Test LLM configuration defaults."""

    def test_defaults(self):
        cfg = LLMConfig()
        assert cfg.enabled is False
        assert cfg.provider == "openai"
        assert cfg.model == "gpt-4o-mini"
        assert cfg.api_key == ""
        assert cfg.min_score_to_notify == 0

    def test_enabled_config(self, llm_config):
        assert llm_config.enabled is True
        assert llm_config.api_key == "test-key"
        assert llm_config.min_score_to_notify == 50

    def test_local_provider(self):
        cfg = LLMConfig(provider="local", base_url="http://localhost:1234/v1")
        assert cfg.provider == "local"
        assert "1234" in cfg.base_url


class TestAppConfig:
    """Test top-level AppConfig composition."""

    def test_defaults(self):
        cfg = AppConfig()
        assert cfg.check_interval_minutes == 15
        assert isinstance(cfg.discord, DiscordConfig)
        assert isinstance(cfg.llm, LLMConfig)
        assert isinstance(cfg.firecrawl, FirecrawlConfig)

    def test_custom(self, app_config):
        assert app_config.check_interval_minutes == 10
        assert app_config.discord.username == "Test Bot"
        assert app_config.llm.enabled is True


class TestFirecrawlConfig:
    """Test Firecrawl configuration defaults."""

    def test_defaults(self):
        cfg = FirecrawlConfig()
        assert cfg.enabled is False
        assert cfg.api_url == "http://localhost:3002"

    def test_custom(self):
        cfg = FirecrawlConfig(enabled=True, api_url="http://my-server:4000")
        assert cfg.enabled is True
        assert cfg.api_url == "http://my-server:4000"
