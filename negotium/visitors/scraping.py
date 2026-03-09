"""
ScrapingVisitor — the concrete visitor that fetches job listings.

Each ``visit_*`` method knows the scraping strategy appropriate for that
category of source.  The source object itself carries the platform-specific
configuration (URLs, selectors, query params, etc.).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import requests
from bs4 import BeautifulSoup

from negotium.models.job import Job

if TYPE_CHECKING:
    from negotium.sources.base import ATSPlatform, CompanyWebsite, JobSearchEngine

from negotium.visitors.base import JobSourceVisitor


class ScrapingVisitor(JobSourceVisitor):
    """Fetches job listings by scraping each source type."""

    # ── Job Search Engines (LinkedIn, Indeed, …) ─────────────────────

    def visit_search_engine(self, source: JobSearchEngine) -> list[Job]:
        """
        Generic strategy for search-engine sources.

        Delegates the actual page fetching & parsing to the source's own
        ``fetch_jobs()`` method, since every engine has a different API /
        HTML structure.
        """
        return source.fetch_jobs()

    # ── Company Career Sites ─────────────────────────────────────────

    def visit_company_site(self, source: CompanyWebsite) -> list[Job]:
        """
        Generic strategy for direct company career pages.

        Each CompanyWebsite subclass implements its own ``fetch_jobs()``
        with site-specific selectors.
        """
        return source.fetch_jobs()

    # ── ATS Platforms (Workday, Oracle Cloud, …) ─────────────────────

    def visit_ats_platform(self, source: ATSPlatform) -> list[Job]:
        """
        Strategy for hosted ATS portals.

        Many ATS platforms expose a JSON API, so this can often bypass
        HTML parsing entirely.  Each ATSPlatform subclass implements
        ``fetch_jobs()`` with the vendor-specific API details.
        """
        return source.fetch_jobs()
