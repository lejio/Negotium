"""Tests for negotium.notification and negotium.discord_notifier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from negotium.config import DiscordConfig
from negotium.discord_notifier import EMBED_COLOR, send_discord_notification
from negotium.models.job import Job
from negotium.notification import notify


# ─── macOS notification ──────────────────────────────────────────────────────


class TestNotify:
    """Test macOS osascript notifications."""

    @patch("negotium.notification.subprocess.run")
    def test_calls_osascript(self, mock_run):
        notify("Test Title", "Test Message")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "osascript"
        assert cmd[1] == "-e"

    @patch("negotium.notification.subprocess.run")
    def test_escapes_quotes_in_title(self, mock_run):
        notify('Title with "quotes"', "msg")
        script = mock_run.call_args[0][0][2]
        assert '\\"' in script
        assert 'Title with \\"quotes\\"' in script

    @patch("negotium.notification.subprocess.run")
    def test_escapes_quotes_in_message(self, mock_run):
        notify("t", 'Say "hello"')
        script = mock_run.call_args[0][0][2]
        assert 'Say \\"hello\\"' in script

    @patch("negotium.notification.subprocess.run")
    def test_includes_sound(self, mock_run):
        notify("t", "m")
        script = mock_run.call_args[0][0][2]
        assert 'sound name "Glass"' in script


# ─── Discord notifications ──────────────────────────────────────────────────


class TestSendDiscordNotification:
    """Test Discord webhook notification sending."""

    def _make_jobs(self, n: int = 1) -> list[Job]:
        return [
            Job(
                title=f"Job {i}",
                company=f"Company {i}",
                location="Remote",
                link=f"https://example.com/{i}",
                posted="1h ago",
                source="Test",
            )
            for i in range(n)
        ]

    def test_does_nothing_when_url_empty(self, disabled_discord_config):
        # Should not raise or call requests
        with patch("negotium.discord_notifier.requests.post") as mock_post:
            send_discord_notification(
                disabled_discord_config, "Test", self._make_jobs()
            )
            mock_post.assert_not_called()

    def test_does_nothing_when_jobs_empty(self, discord_config):
        with patch("negotium.discord_notifier.requests.post") as mock_post:
            send_discord_notification(discord_config, "Test", [])
            mock_post.assert_not_called()

    @patch("negotium.discord_notifier.requests.post")
    def test_sends_webhook(self, mock_post, discord_config):
        mock_post.return_value = MagicMock(status_code=204)
        jobs = self._make_jobs(2)

        send_discord_notification(discord_config, "LinkedIn", jobs)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == discord_config.webhook_url
        payload = kwargs["json"]
        assert "2 New Job(s)" in payload["content"]
        assert "LinkedIn" in payload["content"]
        assert len(payload["embeds"]) == 2
        assert payload["username"] == "Test Bot"

    @patch("negotium.discord_notifier.requests.post")
    def test_embed_fields(self, mock_post, discord_config):
        mock_post.return_value = MagicMock(status_code=204)
        jobs = self._make_jobs(1)

        send_discord_notification(discord_config, "Test", jobs)

        embed = mock_post.call_args[1]["json"]["embeds"][0]
        assert embed["title"] == "Job 0"
        assert embed["url"] == "https://example.com/0"
        assert embed["color"] == EMBED_COLOR
        field_names = {f["name"] for f in embed["fields"]}
        assert "Company" in field_names
        assert "Location" in field_names
        assert "Posted" in field_names

    @patch("negotium.discord_notifier.requests.post")
    def test_includes_match_score(self, mock_post, discord_config):
        mock_post.return_value = MagicMock(status_code=204)
        jobs = self._make_jobs(1)
        jobs[0].match_score = 85

        send_discord_notification(discord_config, "Test", jobs)

        embed = mock_post.call_args[1]["json"]["embeds"][0]
        field_names = {f["name"] for f in embed["fields"]}
        assert "Match Score" in field_names

    @patch("negotium.discord_notifier.requests.post")
    def test_caps_at_10_embeds(self, mock_post, discord_config):
        mock_post.return_value = MagicMock(status_code=204)
        jobs = self._make_jobs(15)

        send_discord_notification(discord_config, "Test", jobs)

        payload = mock_post.call_args[1]["json"]
        assert len(payload["embeds"]) == 10
        assert "showing 10 of 15" in payload["content"]

    @patch("negotium.discord_notifier.requests.post")
    def test_handles_request_exception(self, mock_post, discord_config):
        import requests

        mock_post.side_effect = requests.RequestException("connection failed")
        # Should not raise
        send_discord_notification(discord_config, "Test", self._make_jobs())

    @patch("negotium.discord_notifier.requests.post")
    def test_avatar_url_included(self, mock_post):
        mock_post.return_value = MagicMock(status_code=204)
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/test/t",
            avatar_url="https://example.com/avatar.png",
        )
        send_discord_notification(config, "Test", self._make_jobs())

        payload = mock_post.call_args[1]["json"]
        assert payload["avatar_url"] == "https://example.com/avatar.png"
