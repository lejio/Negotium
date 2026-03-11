"""
FirecrawlVisitor — fetches job listings via the Firecrawl API.

Instead of launching a local Selenium / Chrome process for every page,
this visitor delegates page rendering to a self-hosted Firecrawl instance
(which uses Playwright internally).  Each source still owns its own
HTML parsing logic via ``parse_page()``.

Sources that expose ``build_page_urls()`` and ``parse_page()`` are fetched
through Firecrawl.  Sources that lack those methods (e.g. LinkedIn, which
uses a lightweight ``requests.get()`` call) fall back to their own
``fetch_jobs()`` implementation automatically.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from negotium.firecrawl_client import scrape_page
from negotium.visitors.base import JobSourceVisitor

if TYPE_CHECKING:
    from negotium.models.job import Job
    from negotium.sources.base import ATSPlatform, CompanyWebsite, JobSearchEngine


class FirecrawlVisitor(JobSourceVisitor):
    """Scrapes job sites via a self-hosted Firecrawl instance.

    Parameters
    ----------
    api_url:
        Base URL of the Firecrawl API (e.g. ``http://localhost:3002``).
    """

    def __init__(self, api_url: str = "http://localhost:3002") -> None:
        self.api_url = api_url

    # ── helpers ───────────────────────────────────────────────────────

    def _supports_firecrawl(self, source: object) -> bool:
        """Check whether *source* exposes the Firecrawl interface."""
        return hasattr(source, "build_page_urls") and hasattr(source, "parse_page")

    def _fetch_via_firecrawl(self, source: object) -> list[Job]:
        """Fetch all pages through Firecrawl and delegate parsing."""
        from negotium.models.job import Job  # noqa: F811

        jobs: list[Job] = []
        urls: list[str] = source.build_page_urls()  # type: ignore[attr-defined]

        for url in urls:
            html = scrape_page(url, self.api_url)
            if html is None:
                print(f"  [!] Firecrawl failed for {url}")
                continue
            page_jobs: list[Job] = source.parse_page(html)  # type: ignore[attr-defined]
            jobs.extend(page_jobs)
            if not page_jobs:
                break  # no more results on this page → stop pagination
            time.sleep(1)  # polite rate-limit between pages

        return jobs

    # ── visitor interface ─────────────────────────────────────────────

    def visit_search_engine(self, source: JobSearchEngine) -> list[Job]:
        if self._supports_firecrawl(source):
            return self._fetch_via_firecrawl(source)
        # Fallback: let the source fetch + parse on its own (e.g. LinkedIn)
        return source.fetch_jobs()

    def visit_company_site(self, source: CompanyWebsite) -> list[Job]:
        if self._supports_firecrawl(source):
            return self._fetch_via_firecrawl(source)
        return source.fetch_jobs()

    def visit_ats_platform(self, source: ATSPlatform) -> list[Job]:
        if self._supports_firecrawl(source):
            return self._fetch_via_firecrawl(source)
        return source.fetch_jobs()
