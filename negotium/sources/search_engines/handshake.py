"""Handshake job search engine source (Selenium-based).

.. note::

    Handshake has removed public job browsing — the ``/explore/jobs``
    page now returns a 404.  Browsing jobs requires a student login.
    This source will detect the missing page and return an empty list
    with a log message.  It is kept as a stub so the bot still starts
    cleanly if Handshake is configured.
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
from negotium.sources.driver import make_driver


BASE_URL = "https://joinhandshake.com/explore/jobs"

_HANDSHAKE_DATE_MAP: dict[PostedWithin, str] = {
    PostedWithin.PAST_HOUR: "today",
    PostedWithin.PAST_24H: "today",
    PostedWithin.PAST_WEEK: "this_week",
    PostedWithin.PAST_MONTH: "this_month",
}

_HANDSHAKE_EXPLVL_MAP: dict[ExperienceLevel, str] = {
    ExperienceLevel.INTERNSHIP: "internship",
    ExperienceLevel.ENTRY_LEVEL: "entry_level",
    ExperienceLevel.ASSOCIATE: "entry_level",
    ExperienceLevel.MID_SENIOR: "experienced",
    ExperienceLevel.DIRECTOR: "experienced",
    ExperienceLevel.EXECUTIVE: "experienced",
}


@dataclass
class HandshakeSource(JobSearchEngine):
    """
    Scrapes Handshake's public job listings.

    Handshake is primarily used by college students and recent graduates.

    Usage::

        source = HandshakeSource(
            search=SearchConfig(
                keywords="software engineer",
                experience_levels=[ExperienceLevel.ENTRY_LEVEL],
                location="San Francisco, CA",
            ),
        )
    """

    search: SearchConfig = field(default_factory=SearchConfig)
    max_pages: int = 2

    @property
    def name(self) -> str:
        parts = [f"Handshake ({self.search.keywords})"]
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
            "sort": "recent",
        }

        if page > 1:
            params["page"] = str(page)

        if self.search.location:
            params["location"] = self.search.location

        date_filter = _HANDSHAKE_DATE_MAP.get(self.search.posted_within)
        if date_filter:
            params["posted"] = date_filter

        if self.search.experience_levels:
            level = _HANDSHAKE_EXPLVL_MAP.get(self.search.experience_levels[0])
            if level:
                params["job_type"] = level

        if self.search.remote_only:
            params["remote"] = "true"

        qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        return f"{BASE_URL}?{qs}"

    def fetch_jobs(self) -> list[Job]:
        """Fetch job listings from Handshake using a headless browser.

        Returns an empty list if Handshake's public job page is unavailable.
        """
        jobs: list[Job] = []

        for page_num in range(1, self.max_pages + 1):
            url = self._build_url(page=page_num)
            page_html: str | None = None
            driver = make_driver()
            try:
                driver.get(url)

                # Detect 404 / login-wall — Handshake removed public browsing
                time.sleep(3)
                page_text = driver.page_source.lower()
                if (
                    "right place" in page_text
                    or "page not found" in page_text
                ):
                    print(
                        "  [!] Handshake public job page is no longer available "
                        "(requires student login).  Skipping."
                    )
                    return jobs

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div[data-hook='job-card'], a[class*='job-card'], div[class*='JobCard']")
                    )
                )
                page_html = driver.page_source
            except Exception as exc:
                print(f"  [!] Page load failed — {url}\n      {exc}")
            finally:
                driver.quit()

            if page_html is None:
                continue

            soup = BeautifulSoup(page_html, "html.parser")

            cards = soup.find_all("div", attrs={"data-hook": "job-card"})
            if not cards:
                cards = soup.find_all("a", class_=lambda c: c and "job-card" in str(c))
            if not cards:
                cards = soup.find_all("div", class_=lambda c: c and "JobCard" in str(c))

            if not cards:
                break

            for card in cards:
                # --- title ---
                title_tag = card.find("h3") or card.find(
                    "div", class_=lambda c: c and "title" in str(c).lower()
                )
                title = title_tag.get_text(strip=True) if title_tag else "N/A"

                # --- link ---
                link_tag = card if card.name == "a" else card.find("a", href=True)
                href = link_tag.get("href", "") if link_tag else ""
                if href and not href.startswith("http"):
                    href = f"https://joinhandshake.com{href}"
                link = href.split("?")[0] if href else ""

                # --- company ---
                company_tag = card.find(
                    "div", class_=lambda c: c and "employer" in str(c).lower()
                ) or card.find(
                    "span", class_=lambda c: c and "company" in str(c).lower()
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
