"""ZipRecruiter job search engine source."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from negotium.config import PostedWithin, SearchConfig
from negotium.models.job import Job
from negotium.sources.base import JobSearchEngine


BASE_URL = "https://www.ziprecruiter.com/jobs-search"
RESULTS_PER_PAGE = 20

_ZIP_DAYS_MAP: dict[PostedWithin, str] = {
    PostedWithin.PAST_HOUR: "1",  # no hourly option; use 1 day
    PostedWithin.PAST_24H: "1",
    PostedWithin.PAST_WEEK: "5",
    PostedWithin.PAST_MONTH: "30",
}


@dataclass
class ZipRecruiterSource(JobSearchEngine):
    """
    Scrapes ZipRecruiter's public job listings.

    Usage::

        source = ZipRecruiterSource(
            search=SearchConfig(
                keywords="software engineer",
                location="Austin, TX",
            ),
        )
    """

    search: SearchConfig = field(default_factory=SearchConfig)
    max_pages: int = 2

    @property
    def name(self) -> str:
        parts = [f"ZipRecruiter ({self.search.keywords})"]
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
            "page": str(page),
        }

        if self.search.location:
            params["location"] = self.search.location

        days = _ZIP_DAYS_MAP.get(self.search.posted_within)
        if days:
            params["days"] = days

        if self.search.remote_only:
            params["refine_by_location_type"] = "only_remote"

        qs = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
        return f"{BASE_URL}?{qs}"

    def fetch_jobs(self) -> list[Job]:
        """Fetch job listings from ZipRecruiter."""
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

            # ZipRecruiter wraps listings in article tags or job-card divs
            cards = soup.find_all("article", class_="job_result")
            if not cards:
                cards = soup.find_all("div", class_="job_content")
            if not cards:
                # Try the newer card layout
                cards = soup.find_all("article", attrs={"data-testid": "job-card"})

            if not cards:
                break

            for card in cards:
                # --- title & link ---
                title_tag = (
                    card.find("h2", class_="job_title")
                    or card.find("a", class_="job_link")
                    or card.find("h2")
                )
                title = title_tag.get_text(strip=True) if title_tag else "N/A"

                link_tag = card.find("a", href=True)
                href = link_tag["href"] if link_tag else ""
                if href and not href.startswith("http"):
                    href = f"https://www.ziprecruiter.com{href}"
                link = href.split("?")[0] if href else ""

                # --- company ---
                company_tag = (
                    card.find("a", class_="company_name")
                    or card.find("p", class_="company_name")
                    or card.find("span", class_="company_name")
                )
                company = company_tag.get_text(strip=True) if company_tag else "N/A"

                # --- location ---
                loc_tag = card.find("span", class_="location") or card.find(
                    "p", class_="location"
                )
                location = loc_tag.get_text(strip=True) if loc_tag else "N/A"

                # --- date ---
                date_tag = (
                    card.find("span", class_="posted")
                    or card.find("p", class_="posted")
                    or card.find("time")
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

            time.sleep(2)  # rate-limit

        return jobs
