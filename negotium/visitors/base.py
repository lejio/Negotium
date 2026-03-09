"""
Visitor abstractions — the *Visitor* side of the pattern.

A visitor encapsulates an **operation** that can be performed on every
kind of :class:`~negotium.sources.base.JobSource`.  Adding a new
operation (e.g. validation, export, analytics) only requires a new
visitor — no changes to existing source classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from negotium.models.job import Job
    from negotium.sources.base import ATSPlatform, CompanyWebsite, JobSearchEngine


class JobSourceVisitor(ABC):
    """Interface every visitor must satisfy — one method per element type."""

    @abstractmethod
    def visit_search_engine(self, source: JobSearchEngine) -> list[Job]:
        """Scrape / process a job-search-engine source."""

    @abstractmethod
    def visit_company_site(self, source: CompanyWebsite) -> list[Job]:
        """Scrape / process a direct company career page."""

    @abstractmethod
    def visit_ats_platform(self, source: ATSPlatform) -> list[Job]:
        """Scrape / process a hosted ATS portal."""
