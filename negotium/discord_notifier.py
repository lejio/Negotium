"""
Discord webhook notifier.

Sends rich embeds to a Discord channel via webhook when new jobs are found.
Only sends a message when there are new listings — stays silent otherwise.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from negotium.config import DiscordConfig
    from negotium.models.job import Job


# Discord embed color (a nice blue)
EMBED_COLOR = 0x5865F2


def send_discord_notification(
    config: DiscordConfig,
    source_name: str,
    jobs: list[Job],
) -> None:
    """
    Send a Discord webhook message for new job listings.

    Does nothing if ``config.webhook_url`` is empty or ``jobs`` is empty.
    """
    if not config.webhook_url or not jobs:
        return

    # Build one embed per job (Discord allows up to 10 embeds per message)
    embeds: list[dict] = []
    for job in jobs[:10]:
        embed: dict = {
            "title": job.title,
            "url": job.link,
            "color": EMBED_COLOR,
            "fields": [
                {"name": "Company", "value": job.company, "inline": True},
                {"name": "Location", "value": job.location, "inline": True},
                {"name": "Posted", "value": job.posted, "inline": True},
            ],
        }

        # If the job has an LLM match score, show it
        if hasattr(job, "match_score") and job.match_score is not None:
            embed["fields"].append({
                "name": "Match Score",
                "value": f"**{job.match_score}/100**",
                "inline": True,
            })

        embeds.append(embed)

    payload: dict = {
        "username": config.username,
        "content": f"🔔 **{len(jobs)} New Job(s)** — {source_name}",
        "embeds": embeds,
    }

    if config.avatar_url:
        payload["avatar_url"] = config.avatar_url

    # If more than 10 jobs, note the overflow
    if len(jobs) > 10:
        payload["content"] += f"\n_(showing 10 of {len(jobs)})_"

    try:
        resp = requests.post(config.webhook_url, json=payload, timeout=10)
        if resp.status_code not in (200, 204):
            print(f"  [!] Discord webhook returned {resp.status_code}: {resp.text}")
    except requests.RequestException as exc:
        print(f"  [!] Discord webhook failed: {exc}")
