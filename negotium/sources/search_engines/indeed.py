"""Indeed job search engine source (Selenium-based).

Uses ``undetected-chromedriver`` to reduce bot-detection risk.

.. note::

    Indeed has very aggressive anti-scraping measures.  When run from
    cloud / datacenter IPs the scraper will almost certainly be blocked.
    From a residential IP with ``undetected-chromedriver`` installed it
    has a better chance of succeeding.  If blocked, the source logs a
    warning and returns an empty list—other sources are unaffected.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from urllib.parse import quote

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from negotium.config import ExperienceLevel, PostedWithin, SearchConfig
from negotium.models.job import Job
from negotium.sources.base import JobSearchEngine
from negotium.sources.driver import make_undetected_driver


BASE_URL = "https://www.indeed.com/jobs"
RESULTS_PER_PAGE = 10  # Indeed shows 10 or 15 per page

# Indeed uses different param values than LinkedIn
_INDEED_DATE_MAP: dict[PostedWithin, str] = {
    PostedWithin.PAST_HOUR: "last",  # no exact 1-hour; "last" ≈ recent
    PostedWithin.PAST_24H: "1",
    PostedWithin.PAST_WEEK: "7",
    PostedWithin.PAST_MONTH: "30",
}

_INDEED_EXPLVL_MAP: dict[ExperienceLevel, str] = {
    ExperienceLevel.INTERNSHIP: "INTERNSHIP",
    ExperienceLevel.ENTRY_LEVEL: "ENTRY_LEVEL",
    ExperienceLevel.ASSOCIATE: "MID_LEVEL",
    ExperienceLevel.MID_SENIOR: "MID_LEVEL",
    ExperienceLevel.DIRECTOR: "SENIOR_LEVEL",
    ExperienceLevel.EXECUTIVE: "SENIOR_LEVEL",
}


@dataclass
class IndeedSource(JobSearchEngine):
    """
    Scrapes Indeed's public job listings using Selenium.

    Usage::

        source = IndeedSource(
            search=SearchConfig(
                keywords="software engineer",
                experience_levels=[ExperienceLevel.ENTRY_LEVEL],
                location="New York, NY",
            ),
        )
    """

    search: SearchConfig = field(default_factory=SearchConfig)
    max_pages: int = 2

    @property
    def name(self) -> str:
        parts = [f"Indeed ({self.search.keywords})"]
        if self.search.location:
            parts.append(self.search.location)
        levels = ", ".join(
            lvl.name.replace("_", " ").title() for lvl in self.search.experience_levels
        )
        if levels:
            parts.append(levels)
        return " · ".join(parts)

    # ── Scraping logic ────────────────────────────────────────────────

    def _build_url(self, start: int = 0) -> str:
        params: dict[str, str] = {
            "q": self.search.keywords,
            "sort": "date",  # newest first
            "start": str(start),
        }

        if self.search.location:
            params["l"] = self.search.location

        # Time filter → fromage
        fromage = _INDEED_DATE_MAP.get(self.search.posted_within)
        if fromage and fromage != "last":
            params["fromage"] = fromage

        # Experience level → sc (Indeed uses a 0kf format)
        if self.search.experience_levels:
            level = _INDEED_EXPLVL_MAP.get(self.search.experience_levels[0])
            if level:
                params["sc"] = f"0kf:explvl({level});"

        if self.search.remote_only:
            params["remotejob"] = "032b3046-06a3-4876-8dfd-474eb5e7ed11"

        qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        return f"{BASE_URL}?{qs}"

    # ── Firecrawl-compatible interface ────────────────────────────────

    def build_page_urls(self) -> list[str]:
        """Return URLs for every page to scrape."""
        return [
            self._build_url(start=p * RESULTS_PER_PAGE)
            for p in range(self.max_pages)
        ]

    def parse_page(self, html: str) -> list[Job]:
        """Parse a single Indeed results page into :class:`Job` objects.

        Returns an empty list if a block/CAPTCHA page is detected.
        """
        jobs: list[Job] = []
        soup = BeautifulSoup(html, "html.parser")

        # Detect hard blocks in the HTML itself
        title_tag = soup.find("title")
        if title_tag and "blocked" in title_tag.get_text().lower():
            print(
                "  [!] Indeed blocked this request "
                "(likely datacenter / cloud IP).  Skipping."
            )
            return jobs

        cards = soup.find_all("div", class_="job_seen_beacon")
        if not cards:
            cards = soup.find_all("div", class_="jobsearch-SerpJobCard")

        for card in cards:
            title_el = card.find("h2", class_="jobTitle") or card.find(
                "a", class_="jcs-JobTitle"
            )
            title = title_el.get_text(strip=True) if title_el else "N/A"

            link_tag = card.find("a", href=True)
            href = link_tag["href"] if link_tag else ""
            if href and not href.startswith("http"):
                href = f"https://www.indeed.com{href}"
            link = href.split("&")[0] if href else ""

            company_tag = card.find(
                "span", attrs={"data-testid": "company-name"}
            ) or card.find("span", class_="companyName")
            company = company_tag.get_text(strip=True) if company_tag else "N/A"

            loc_tag = card.find(
                "div", attrs={"data-testid": "text-location"}
            ) or card.find("div", class_="companyLocation")
            location = loc_tag.get_text(strip=True) if loc_tag else "N/A"

            date_tag = card.find("span", class_="date")
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

        return jobs

    # ── Selenium-based fetch (used by ScrapingVisitor) ────────────

    def fetch_jobs(self) -> list[Job]:
        """Fetch job listings from Indeed using an undetected headless browser.

        Returns an empty list if Indeed blocks the request.
        """
        jobs: list[Job] = []

        for url in self.build_page_urls():
            page_html: str | None = None
            driver = make_undetected_driver()
            try:
                driver.get(url)
                time.sleep(3)

                if "Blocked" in driver.title or "bot-detection" in driver.current_url:
                    print(
                        "  [!] Indeed blocked this request "
                        "(likely datacenter / cloud IP).  Skipping."
                    )
                    return jobs

                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.job_seen_beacon, div.jobsearch-SerpJobCard")
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

            time.sleep(2)

        return jobs
