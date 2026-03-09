"""Indeed job search engine source."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from negotium.config import ExperienceLevel, PostedWithin, SearchConfig
from negotium.models.job import Job
from negotium.sources.base import JobSearchEngine


BASE_URL = "https://www.indeed.com/jobs"
RESULTS_PER_PAGE = 10  # Indeed shows 10 or 15 per page

# Indeed uses different param values than LinkedIn
_INDEED_DATE_MAP: dict[PostedWithin, str] = {
    PostedWithin.PAST_HOUR:  "last",     # no exact 1-hour; "last" ≈ recent
    PostedWithin.PAST_24H:   "1",
    PostedWithin.PAST_WEEK:  "7",
    PostedWithin.PAST_MONTH: "30",
}

_INDEED_EXPLVL_MAP: dict[ExperienceLevel, str] = {
    ExperienceLevel.INTERNSHIP:  "INTERNSHIP",
    ExperienceLevel.ENTRY_LEVEL: "ENTRY_LEVEL",
    ExperienceLevel.ASSOCIATE:   "MID_LEVEL",
    ExperienceLevel.MID_SENIOR:  "MID_LEVEL",
    ExperienceLevel.DIRECTOR:    "SENIOR_LEVEL",
    ExperienceLevel.EXECUTIVE:   "SENIOR_LEVEL",
}


@dataclass
class IndeedSource(JobSearchEngine):
    """
    Scrapes Indeed's public job listings.

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
        levels = ", ".join(lvl.name.replace("_", " ").title()
                          for lvl in self.search.experience_levels)
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

        qs = "&".join(
            f"{k}={requests.utils.quote(str(v))}" for k, v in params.items()
        )
        return f"{BASE_URL}?{qs}"

    def fetch_jobs(self) -> list[Job]:
        """Fetch job listings from Indeed."""
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

            # Indeed wraps each listing in a div with class "job_seen_beacon"
            # or a <td> with class "resultContent"
            cards = soup.find_all("div", class_="job_seen_beacon")
            if not cards:
                # fallback: older markup
                cards = soup.find_all("div", class_="jobsearch-SerpJobCard")

            if not cards:
                break

            for card in cards:
                # --- title & link ---
                title_tag = (
                    card.find("h2", class_="jobTitle")
                    or card.find("a", class_="jcs-JobTitle")
                )
                title = title_tag.get_text(strip=True) if title_tag else "N/A"

                link_tag = card.find("a", href=True)
                href = link_tag["href"] if link_tag else ""
                if href and not href.startswith("http"):
                    href = f"https://www.indeed.com{href}"
                link = href.split("&")[0] if href else ""  # clean tracking params

                # --- company ---
                company_tag = (
                    card.find("span", attrs={"data-testid": "company-name"})
                    or card.find("span", class_="companyName")
                )
                company = company_tag.get_text(strip=True) if company_tag else "N/A"

                # --- location ---
                loc_tag = (
                    card.find("div", attrs={"data-testid": "text-location"})
                    or card.find("div", class_="companyLocation")
                )
                location = loc_tag.get_text(strip=True) if loc_tag else "N/A"

                # --- date ---
                date_tag = card.find("span", class_="date")
                posted = date_tag.get_text(strip=True) if date_tag else "N/A"

                if link:
                    jobs.append(Job(
                        title=title,
                        company=company,
                        location=location,
                        link=link,
                        posted=posted,
                        source=self.name,
                    ))

            time.sleep(2)  # rate-limit

        return jobs
