"""Glassdoor job search engine source."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from negotium.config import ExperienceLevel, PostedWithin, SearchConfig
from negotium.models.job import Job
from negotium.sources.base import JobSearchEngine


BASE_URL = "https://www.glassdoor.com/Job/jobs.htm"

# Glassdoor fromAge param (days)
_GD_DATE_MAP: dict[PostedWithin, str] = {
    PostedWithin.PAST_HOUR:  "1",
    PostedWithin.PAST_24H:   "1",
    PostedWithin.PAST_WEEK:  "7",
    PostedWithin.PAST_MONTH: "30",
}

# Glassdoor seniorityType IDs
_GD_SENIORITY_MAP: dict[ExperienceLevel, str] = {
    ExperienceLevel.INTERNSHIP:  "internship",
    ExperienceLevel.ENTRY_LEVEL: "entrylevel",
    ExperienceLevel.ASSOCIATE:   "midseniorlevel",
    ExperienceLevel.MID_SENIOR:  "midseniorlevel",
    ExperienceLevel.DIRECTOR:    "director",
    ExperienceLevel.EXECUTIVE:   "executive",
}


@dataclass
class GlassdoorSource(JobSearchEngine):
    """
    Scrapes Glassdoor's public job listings.

    Usage::

        source = GlassdoorSource(
            search=SearchConfig(
                keywords="software engineer",
                experience_levels=[ExperienceLevel.ENTRY_LEVEL],
                location="Seattle, WA",
            ),
        )
    """

    search: SearchConfig = field(default_factory=SearchConfig)
    max_pages: int = 2

    @property
    def name(self) -> str:
        parts = [f"Glassdoor ({self.search.keywords})"]
        if self.search.location:
            parts.append(self.search.location)
        levels = ", ".join(lvl.name.replace("_", " ").title()
                          for lvl in self.search.experience_levels)
        if levels:
            parts.append(levels)
        return " · ".join(parts)

    @property
    def headers(self) -> dict[str, str]:
        """Glassdoor needs a slightly different user-agent to avoid blocks."""
        return {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.glassdoor.com/",
        }

    # ── Scraping logic ────────────────────────────────────────────────

    def _build_url(self, page: int = 1) -> str:
        params: dict[str, str] = {
            "sc.keyword": self.search.keywords,
            "sortBy": "date",
        }

        if page > 1:
            params["p"] = str(page)

        if self.search.location:
            params["locT"] = "C"  # city
            params["locKeyword"] = self.search.location

        fromage = _GD_DATE_MAP.get(self.search.posted_within)
        if fromage:
            params["fromAge"] = fromage

        if self.search.experience_levels:
            seniority = _GD_SENIORITY_MAP.get(self.search.experience_levels[0])
            if seniority:
                params["seniorityType"] = seniority

        if self.search.remote_only:
            params["remoteWorkType"] = "1"

        qs = "&".join(
            f"{k}={requests.utils.quote(str(v))}" for k, v in params.items()
        )
        return f"{BASE_URL}?{qs}"

    def fetch_jobs(self) -> list[Job]:
        """Fetch job listings from Glassdoor."""
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

            # Glassdoor uses <li> with data-test="jobListing" or
            # <a> cards with class "JobCard_jobCardContainer"
            cards = soup.find_all("li", attrs={"data-test": "jobListing"})
            if not cards:
                cards = soup.find_all("li", class_="JobsList_jobListItem__wjTHv")
            if not cards:
                # Broader fallback — any job card anchor
                cards = soup.find_all("a", class_=lambda c: c and "JobCard" in c)

            if not cards:
                break

            for card in cards:
                # --- title ---
                title_tag = (
                    card.find("a", attrs={"data-test": "job-title"})
                    or card.find("a", class_=lambda c: c and "jobTitle" in str(c))
                    or card.find("h2")
                )
                title = title_tag.get_text(strip=True) if title_tag else "N/A"

                # --- link ---
                link_tag = title_tag if title_tag and title_tag.name == "a" else card.find("a", href=True)
                href = link_tag.get("href", "") if link_tag else ""
                if href and not href.startswith("http"):
                    href = f"https://www.glassdoor.com{href}"
                link = href.split("?")[0] if href else ""

                # --- company ---
                company_tag = (
                    card.find("span", class_=lambda c: c and "EmployerName" in str(c))
                    or card.find("div", attrs={"data-test": "emp-name"})
                    or card.find("span", class_=lambda c: c and "companyName" in str(c))
                )
                company = company_tag.get_text(strip=True) if company_tag else "N/A"

                # --- location ---
                loc_tag = (
                    card.find("span", attrs={"data-test": "emp-location"})
                    or card.find("div", class_=lambda c: c and "location" in str(c).lower())
                )
                location = loc_tag.get_text(strip=True) if loc_tag else "N/A"

                # --- date ---
                date_tag = (
                    card.find("div", attrs={"data-test": "job-age"})
                    or card.find("span", class_=lambda c: c and "listingAge" in str(c))
                )
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

            time.sleep(2.5)  # Glassdoor is stricter on rate-limiting

        return jobs
