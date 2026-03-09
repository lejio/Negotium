"""
Negotium — Extensible Job Alert Bot

Uses the Visitor pattern to support multiple source types:
  • Job search engines  (LinkedIn, Indeed, Glassdoor, …)
  • Company career sites (apple.com/careers, …)
  • ATS platforms        (Workday, Oracle Cloud, Greenhouse, …)

Adding a new source = one new class.  Adding a new operation = one new visitor.
"""

import time
from datetime import datetime

import schedule

from negotium.config import (
    AppConfig,
    DiscordConfig,
    ExperienceLevel,
    LLMConfig,
    PostedWithin,
    SearchConfig,
)
from negotium.discord_notifier import send_discord_notification
from negotium.notification import notify
from negotium.persistence import load_seen_jobs, save_seen_jobs
from negotium.ranker import rank_jobs
from negotium.sources.base import JobSource
from negotium.sources.search_engines.linkedin import LinkedInSource
from negotium.sources.search_engines.indeed import IndeedSource
from negotium.sources.search_engines.ziprecruiter import ZipRecruiterSource
from negotium.sources.search_engines.glassdoor import GlassdoorSource
from negotium.visitors.scraping import ScrapingVisitor

# ─── Configuration ───────────────────────────────────────────────────────────

CONFIG = AppConfig(
    check_interval_minutes=15,

    # ── Discord webhook (leave url empty to disable) ──────────────────
    discord=DiscordConfig(
        webhook_url="",                  # paste your webhook URL here
        username="Negotium Bot",
    ),

    # ── LLM job ranking (set enabled=True to activate) ────────────────
    # Provider options:
    #   "openai" — uses OpenAI API (needs api_key or OPENAI_API_KEY env var)
    #   "local"  — uses any OpenAI-compatible local server:
    #              Ollama (localhost:11434), LM Studio (localhost:1234),
    #              llama.cpp (localhost:8080), vLLM (localhost:8000), etc.
    llm=LLMConfig(
        enabled=False,
        provider="openai",               # "openai" or "local"
        model="gpt-4o-mini",             # or e.g. "llama3.2" for Ollama
        api_key="",                      # or set OPENAI_API_KEY env var
        base_url="http://localhost:11434/v1",  # only used when provider="local"
        resume_path=__import__("pathlib").Path("resume.txt"),
        min_score_to_notify=0,           # only notify for jobs >= this score
    ),
)

# ── Sources to monitor ───────────────────────────────────────────────────────

SOURCES: list[JobSource] = [
    LinkedInSource(
        search=SearchConfig(
            keywords="software engineer",
            experience_levels=[ExperienceLevel.ENTRY_LEVEL],
            posted_within=PostedWithin.PAST_24H,
            location="",                 # e.g. "San Francisco, CA"
            remote_only=False,
        ),
    ),
    # ── Add more sources (uncomment to enable) ───────────────────────
    IndeedSource(
        search=SearchConfig(
            keywords="software engineer",
            experience_levels=[ExperienceLevel.ENTRY_LEVEL],
            location="New York, NY",
        ),
    ),
    ZipRecruiterSource(
        search=SearchConfig(
            keywords="software engineer",
            location="New York, NY",
        ),
    ),
    GlassdoorSource(
        search=SearchConfig(
            keywords="software engineer",
            experience_levels=[ExperienceLevel.ENTRY_LEVEL],
            location="New York, NY",
        ),
    ),
]


# ─── Core Loop ───────────────────────────────────────────────────────────────

def check_for_new_jobs() -> None:
    """Run one check cycle: visit every source, diff, rank, notify, persist."""
    visitor = ScrapingVisitor()
    seen = load_seen_jobs()
    new_total = 0

    for source in SOURCES:
        print(f"\n[*] {source.name}  ({datetime.now().strftime('%H:%M:%S')})")

        # Visitor double-dispatch: source.accept() → visitor.visit_*(source)
        jobs = source.accept(visitor)
        new_jobs = [j for j in jobs if j.job_id not in seen]

        if not new_jobs:
            print("    — No new listings.")
            continue

        # ── LLM ranking (if enabled) ─────────────────────────────────
        if CONFIG.llm.enabled:
            new_jobs = rank_jobs(new_jobs, CONFIG.llm)
            # Filter by minimum score
            if CONFIG.llm.min_score_to_notify > 0:
                new_jobs = [
                    j for j in new_jobs
                    if j.match_score is None
                    or j.match_score < 0
                    or j.match_score >= CONFIG.llm.min_score_to_notify
                ]

        new_total += len(new_jobs)

        print(f"    ✅ {len(new_jobs)} new listing(s) found!")
        for j in new_jobs:
            score_str = f" [Score: {j.match_score}/100]" if j.match_score is not None else ""
            print(f"       • {j.title} @ {j.company} — {j.location}{score_str}")
            print(f"         {j.link}")
            print(f"         Posted: {j.posted}")
            seen.add(j.job_id)

        # ── macOS notification ────────────────────────────────────────
        titles = ", ".join(j.title for j in new_jobs[:3])
        extra = f" (+{len(new_jobs) - 3} more)" if len(new_jobs) > 3 else ""
        notify(
            f"🔔 {len(new_jobs)} New Job(s) — {source.name}",
            f"{titles}{extra}",
        )

        # ── Discord notification (only if configured) ─────────────────
        send_discord_notification(CONFIG.discord, source.name, new_jobs)

    save_seen_jobs(seen)
    print(f"\n[✓] Cycle done. {new_total} new job(s) across "
          f"{len(SOURCES)} source(s). "
          f"Next check in {CONFIG.check_interval_minutes} min.\n")


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print(" Negotium — Job Alert Bot")
    print(f" Checking every {CONFIG.check_interval_minutes} minutes")
    print(f" Sources: {[s.name for s in SOURCES]}")
    print(f" Discord: {'✅ enabled' if CONFIG.discord.webhook_url else '❌ disabled'}")
    print(f" LLM Ranking: {'✅ enabled' if CONFIG.llm.enabled else '❌ disabled'}")
    print("=" * 60)

    # run immediately on start
    check_for_new_jobs()

    # then schedule periodic checks
    schedule.every(CONFIG.check_interval_minutes).minutes.do(check_for_new_jobs)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[x] Stopped by user. Goodbye!")


if __name__ == "__main__":
    main()
