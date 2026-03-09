"""
Job source abstractions — the *Element* side of the Visitor pattern.

Three concrete element categories exist:

  JobSearchEngine   – aggregator sites  (LinkedIn, Indeed, Glassdoor …)
  CompanyWebsite    – direct career pages (apple.com/careers, …)
  ATSPlatform       – hosted ATS portals  (Workday, Oracle Cloud, Greenhouse …)

Each category routes to a dedicated ``visit_*`` method on any
:class:`~negotium.visitors.base.JobSourceVisitor`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from negotium.models.job import Job
    from negotium.visitors.base import JobSourceVisitor


class JobSource(ABC):
    """Base element that every job source must implement."""

    # ── identity ──────────────────────────────────────────────────────

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name shown in logs & notifications."""

    # ── visitor entry-point ───────────────────────────────────────────

    @abstractmethod
    def accept(self, visitor: JobSourceVisitor) -> list[Job]:
        """Double-dispatch: call the correct ``visit_*`` on *visitor*."""

    # ── per-source config (optional overrides) ────────────────────────

    @property
    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }


# ─── Three element categories ────────────────────────────────────────────────


class JobSearchEngine(JobSource):
    """Aggregator job boards — LinkedIn, Indeed, Glassdoor, etc."""

    def accept(self, visitor: JobSourceVisitor) -> list[Job]:
        return visitor.visit_search_engine(self)


class CompanyWebsite(JobSource):
    """First-party company career pages (e.g. apple.com/careers)."""

    def accept(self, visitor: JobSourceVisitor) -> list[Job]:
        return visitor.visit_company_site(self)


class ATSPlatform(JobSource):
    """Hosted ATS portals — Workday, Oracle Cloud, Greenhouse, etc."""

    @property
    @abstractmethod
    def platform(self) -> str:
        """ATS vendor name, e.g. 'workday', 'oracle'."""

    @property
    @abstractmethod
    def company_name(self) -> str:
        """Company whose ATS portal this is."""

    def accept(self, visitor: JobSourceVisitor) -> list[Job]:
        return visitor.visit_ats_platform(self)
