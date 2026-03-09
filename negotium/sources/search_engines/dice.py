"""Dice job search engine source."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from negotium.config import ExperienceLevel, PostedWithin, SearchConfig
from negotium.models.job import Job
from negotium.sources.base import JobSearchEngine


BASE_URL = "https://www.dice.com/jobs"

_DICE_DATE_MAP: dict[PostedWithin, str] = {
    PostedWithin.PAST_HOUR: "ONE",
    PostedWithin.PAST_24H: "ONE",
    PostedWithin.PAST_WEEK: "SEVEN",
    PostedWithin.PAST_MONTH: "THIRTY",
}

_DICE_EXPLVL_MAP: dict[ExperienceLevel, str] = {
    ExperienceLevel.INTERNSHIP: "ENTRY",
    ExperienceLevel.ENTRY_LEVEL: "ENTRY",
    ExperienceLevel.ASSOCIATE: "MID",
    ExperienceLevel.MID_SENIOR: "SENIOR",
    ExperienceLevel.DIRECTOR: "SENIOR",
    ExperienceLevel.EXECUTIVE: "SENIOR",
}


@dataclass
class DiceSource(JobSearchEngine):
    """
    Scrapes Dice's public job listings.

    Dice specializes in tech and IT jobs.

    Usage::

        source = DiceSource(
            search=SearchConfig(
                keywords="python developer",
                experience_levels=[ExperienceLevel.MID_SENIOR],
                location="Austin, TX",
            ),
        )
    """

    search: SearchConfig = field(default_factory=SearchConfig)
    max_pages: int = 2

    @property
    def name(self) -> str:
        parts = [f"Dice ({self.search.keywords})"]
        if self.search.location:
            parts.append(self.search.location)
        levels = ", ".join(
            lvl.name.replace("_", " ").title() for lvl in self.search.experience_levels
        )
        if levels:
            parts.append(levels)
        return " · ".join(parts)

    # ── Scraping logic ────────────────────────────────────────────────

    def _build_url(self, page: int = 1) -> str:
        params: dict[str, str] = {
            "q": self.search.keywords,
            "countryCode": "US",
            "radius": "30",
            "radiusUnit": "mi",
            "page": str(page),
            "pageSize": "20",
            "language": "en",
        }

        if self.search.location:
            params["location"] = self.search.location

        date_filter = _DICE_DATE_MAP.get(self.search.posted_within)
        if date_filter:
            params["filters.postedDate"] = date_filter

        if self.search.experience_levels:
            level = _DICE_EXPLVL_MAP.get(self.search.experience_levels[0])
            if level:
                params["filters.experienceLevel"] = level

        if self.search.remote_only:
            params["filters.isRemote"] = "true"

        qs = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
        return f"{BASE_URL}?{qs}"

    def fetch_jobs(self) -> list[Job]:
        """Fetch job listings from Dice."""
        jobs: list[Job] = []

        for page_num in range(1, self.max_pages + 1):
            url = self._build_url(page=page_num)
            try:
                resp = requests.get(url, headers=self.headers, timeout=15)
                if resp.status_code != 200:
                    print(f"  [!] HTTP {resp.status_code} — {url}")
                    break
            except requests.RequestException as exc:
                print(f"  [!] Request failed: {exc}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")

            # Dice uses custom web components / shadow DOM; fall back to
            # common selectors for server-rendered content
            cards = soup.find_all("dhi-search-card")
            if not cards:
                cards = soup.find_all(
                    "div", class_=lambda c: c and "card" in str(c).lower()
                )
            if not cards:
                cards = soup.find_all("a", attrs={"data-cy": "card-title-link"})

            if not cards:
                break

            for card in cards:
                # --- title & link ---
                title_tag = card.find(
                    "a", attrs={"data-cy": "card-title-link"}
                ) or card.find("a", class_=lambda c: c and "title" in str(c).lower())
                if not title_tag:
                    title_tag = card.find("h5") or card.find("h3")

                title = title_tag.get_text(strip=True) if title_tag else "N/A"

                link_tag = (
                    title_tag
                    if title_tag and title_tag.name == "a"
                    else card.find("a", href=True)
                )
                href = link_tag.get("href", "") if link_tag else ""
                if href and not href.startswith("http"):
                    href = f"https://www.dice.com{href}"
                link = href.split("?")[0] if href else ""

                # --- company ---
                company_tag = card.find(
                    "a", attrs={"data-cy": "search-result-company-name"}
                ) or card.find(
                    "span", class_=lambda c: c and "company" in str(c).lower()
                )
                company = company_tag.get_text(strip=True) if company_tag else "N/A"

                # --- location ---
                loc_tag = card.find(
                    "span", attrs={"data-cy": "search-result-location"}
                ) or card.find(
                    "span", class_=lambda c: c and "location" in str(c).lower()
                )
                location = loc_tag.get_text(strip=True) if loc_tag else "N/A"

                # --- date ---
                date_tag = card.find(
                    "span", attrs={"data-cy": "card-posted-date"}
                ) or card.find(
                    "span", class_=lambda c: c and "posted" in str(c).lower()
                )
                posted = date_tag.get_text(strip=True) if date_tag else "N/A"

                if link:
                    jobs.append(
                        Job(
                            title=title,
                            company=company,
                            location=location,
                            link=link,
                            posted=posted,
                            source=self.name,
                        )
                    )

            time.sleep(2)

        return jobs
