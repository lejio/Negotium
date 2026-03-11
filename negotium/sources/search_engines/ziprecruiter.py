"""ZipRecruiter job search engine source (Selenium-based)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from urllib.parse import quote

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from negotium.config import PostedWithin, SearchConfig
from negotium.models.job import Job
from negotium.sources.base import JobSearchEngine
from negotium.sources.driver import make_driver


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

        qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        return f"{BASE_URL}?{qs}"

    # ── Firecrawl-compatible interface ────────────────────────────────

    def build_page_urls(self) -> list[str]:
        """Return URLs for every page to scrape."""
        return [self._build_url(page=p) for p in range(1, self.max_pages + 1)]

    def parse_page(self, html: str) -> list[Job]:
        """Parse a single ZipRecruiter results page into :class:`Job` objects."""
        jobs: list[Job] = []
        soup = BeautifulSoup(html, "html.parser")

        # ── Extract job URLs from JSON-LD structured data ─────────
        jsonld_urls: list[str] = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict) and data.get("@type") == "ItemList":
                    for item in data.get("itemListElement", []):
                        jsonld_urls.append(item.get("url", ""))
            except (json.JSONDecodeError, TypeError):
                pass

        # ── Parse HTML cards ──────────────────────────────────────
        cards = soup.find_all("div", class_="job_result_two_pane_v2")

        for i, card in enumerate(cards):
            article = card.find("article")
            if not article:
                continue

            h2 = article.find("h2")
            title = h2.get_text(strip=True) if h2 else "N/A"

            link = jsonld_urls[i] if i < len(jsonld_urls) else ""

            company_tag = article.find(
                "a", attrs={"data-testid": "job-card-company"}
            )
            company = company_tag.get_text(strip=True) if company_tag else "N/A"

            loc_tag = article.find(
                "a", attrs={"data-testid": "job-card-location"}
            )
            location = loc_tag.get_text(strip=True) if loc_tag else "N/A"

            posted = "N/A"

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

        return jobs

    # ── Selenium-based fetch (used by ScrapingVisitor) ────────────

    def fetch_jobs(self) -> list[Job]:
        """Fetch job listings from ZipRecruiter using a headless browser."""
        jobs: list[Job] = []

        for url in self.build_page_urls():
            page_html: str | None = None
            driver = make_driver()
            try:
                driver.get(url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.job_result_two_pane_v2")
                    )
                )
                page_html = driver.page_source
            except Exception as exc:
                print(f"  [!] Page load failed — {url}\n      {exc}")
            finally:
                driver.quit()

            if page_html is None:
                continue

            page_jobs = self.parse_page(page_html)
            jobs.extend(page_jobs)

            if not page_jobs:
                break

            time.sleep(2)  # rate-limit

        return jobs
