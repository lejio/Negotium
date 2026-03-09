"""FlexJobs job search engine source."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from negotium.config import ExperienceLevel, PostedWithin, SearchConfig
from negotium.models.job import Job
from negotium.sources.base import JobSearchEngine


BASE_URL = "https://www.flexjobs.com/search"

_FLEX_DATE_MAP: dict[PostedWithin, str] = {
    PostedWithin.PAST_HOUR: "1",
    PostedWithin.PAST_24H: "1",
    PostedWithin.PAST_WEEK: "7",
    PostedWithin.PAST_MONTH: "30",
}

_FLEX_EXPLVL_MAP: dict[ExperienceLevel, str] = {
    ExperienceLevel.INTERNSHIP: "Entry-Level",
    ExperienceLevel.ENTRY_LEVEL: "Entry-Level",
    ExperienceLevel.ASSOCIATE: "Experienced",
    ExperienceLevel.MID_SENIOR: "Manager",
    ExperienceLevel.DIRECTOR: "Senior-Manager",
    ExperienceLevel.EXECUTIVE: "Executive",
}


@dataclass
class FlexJobsSource(JobSearchEngine):
    """
    Scrapes FlexJobs' public job listings.

    FlexJobs focuses on remote, part-time, freelance, and flexible jobs.

    Usage::

        source = FlexJobsSource(
            search=SearchConfig(
                keywords="software engineer",
                experience_levels=[ExperienceLevel.ENTRY_LEVEL],
                remote_only=True,
            ),
        )
    """

    search: SearchConfig = field(default_factory=SearchConfig)
    max_pages: int = 2

    @property
    def name(self) -> str:
        parts = [f"FlexJobs ({self.search.keywords})"]
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
            "search": self.search.keywords,
        }

        if page > 1:
            params["page"] = str(page)

        if self.search.location:
            params["location"] = self.search.location

        date_filter = _FLEX_DATE_MAP.get(self.search.posted_within)
        if date_filter:
            params["within_days"] = date_filter

        if self.search.experience_levels:
            level = _FLEX_EXPLVL_MAP.get(self.search.experience_levels[0])
            if level:
                params["experience"] = level

        if self.search.remote_only:
            params["tele_type"] = "100%25-Telecommuting"

        qs = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
        return f"{BASE_URL}?{qs}"

    def fetch_jobs(self) -> list[Job]:
        """Fetch job listings from FlexJobs."""
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

            cards = soup.find_all("div", class_="job-card")
            if not cards:
                cards = soup.find_all(
                    "li", class_=lambda c: c and "job" in str(c).lower()
                )
            if not cards:
                cards = soup.find_all(
                    "div", class_=lambda c: c and "listing" in str(c).lower()
                )

            if not cards:
                break

            for card in cards:
                # --- title & link ---
                title_tag = card.find(
                    "a", class_=lambda c: c and "title" in str(c).lower()
                )
                if not title_tag:
                    title_tag = (
                        card.find("h5") or card.find("h3") or card.find("a", href=True)
                    )
                title = title_tag.get_text(strip=True) if title_tag else "N/A"

                link_tag = (
                    title_tag
                    if title_tag and title_tag.name == "a"
                    else card.find("a", href=True)
                )
                href = link_tag.get("href", "") if link_tag else ""
                if href and not href.startswith("http"):
                    href = f"https://www.flexjobs.com{href}"
                link = href.split("?")[0] if href else ""

                # --- company ---
                company_tag = card.find(
                    "span", class_=lambda c: c and "company" in str(c).lower()
                ) or card.find(
                    "div", class_=lambda c: c and "employer" in str(c).lower()
                )
                company = company_tag.get_text(strip=True) if company_tag else "N/A"

                # --- location ---
                loc_tag = card.find(
                    "span", class_=lambda c: c and "location" in str(c).lower()
                ) or card.find(
                    "div", class_=lambda c: c and "location" in str(c).lower()
                )
                location = loc_tag.get_text(strip=True) if loc_tag else "N/A"

                # --- date ---
                date_tag = card.find(
                    "span", class_=lambda c: c and "date" in str(c).lower()
                ) or card.find("time")
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
