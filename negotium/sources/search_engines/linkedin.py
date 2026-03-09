"""LinkedIn job search engine source."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from negotium.config import SearchConfig, ExperienceLevel, PostedWithin
from negotium.models.job import Job
from negotium.sources.base import JobSearchEngine


BASE_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
)
RESULTS_PER_PAGE = 25


@dataclass
class LinkedInSource(JobSearchEngine):
    """
    Scrapes LinkedIn's public (guest) job listings API.

    Usage::

        source = LinkedInSource(
            search=SearchConfig(
                keywords="software engineer",
                experience_levels=[ExperienceLevel.ENTRY_LEVEL],
                location="San Francisco, CA",
            ),
        )
    """

    search: SearchConfig = field(default_factory=SearchConfig)
    max_pages: int = 2

    # ── JobSource interface ───────────────────────────────────────────

    @property
    def name(self) -> str:
        parts = [f"LinkedIn ({self.search.keywords})"]
        if self.search.location:
            parts.append(self.search.location)
        levels = ", ".join(lvl.name.replace("_", " ").title()
                          for lvl in self.search.experience_levels)
        if levels:
            parts.append(levels)
        return " · ".join(parts)

    # ── Scraping logic ────────────────────────────────────────────────

    def _build_url(self, start: int = 0) -> str:
        params: dict[str, str] = {
            "keywords": self.search.keywords,
            "start": str(start),
            "sortBy": "DD",                              # newest first
            "f_TPR": self.search.posted_within.value,
            "f_E": self.search.experience_filter_value,
        }
        if self.search.location:
            params["location"] = self.search.location
        if self.search.remote_only:
            params["f_WT"] = "2"  # remote work type

        qs = "&".join(
            f"{k}={requests.utils.quote(str(v))}" for k, v in params.items()
        )
        return f"{BASE_URL}?{qs}"

    def fetch_jobs(self) -> list[Job]:
        """Fetch job listings from LinkedIn's public API."""
        jobs: list[Job] = []

        for page in range(self.max_pages):
            url = self._build_url(start=page * RESULTS_PER_PAGE)
            try:
                resp = requests.get(url, headers=self.headers, timeout=15)
                if resp.status_code != 200:
                    print(f"  [!] HTTP {resp.status_code} — {url}")
                    break
            except requests.RequestException as exc:
                print(f"  [!] Request failed: {exc}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_="base-card")

            if not cards:
                break

            for card in cards:
                title_tag = card.find("h3", class_="base-search-card__title")
                link_tag = card.find("a", class_="base-card__full-link")
                title = title_tag.get_text(strip=True) if title_tag else "N/A"
                link = link_tag["href"].split("?")[0] if link_tag else ""

                company_tag = card.find("h4", class_="base-search-card__subtitle")
                company = company_tag.get_text(strip=True) if company_tag else "N/A"

                loc_tag = card.find("span", class_="job-search-card__location")
                location = loc_tag.get_text(strip=True) if loc_tag else "N/A"

                time_tag = card.find("time")
                posted = time_tag.get_text(strip=True) if time_tag else "N/A"

                if link:
                    jobs.append(Job(
                        title=title,
                        company=company,
                        location=location,
                        link=link,
                        posted=posted,
                        source=self.name,
                    ))

            time.sleep(1.5)  # rate-limit between pages

        return jobs
