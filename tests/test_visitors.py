"""Tests for negotium.visitors — visitor pattern dispatch."""

from __future__ import annotations

from unittest.mock import MagicMock

from negotium.models.job import Job
from negotium.sources.search_engines.linkedin import LinkedInSource
from negotium.visitors.scraping import ScrapingVisitor


class TestScrapingVisitor:
    """Test that ScrapingVisitor delegates to source.fetch_jobs()."""

    def test_visit_search_engine_delegates(self):
        visitor = ScrapingVisitor()
        source = MagicMock()
        expected = [
            Job(
                title="T",
                company="C",
                location="L",
                link="https://x.com/1",
                posted="now",
            )
        ]
        source.fetch_jobs.return_value = expected

        result = visitor.visit_search_engine(source)

        source.fetch_jobs.assert_called_once()
        assert result == expected

    def test_visit_search_engine_empty(self):
        visitor = ScrapingVisitor()
        source = MagicMock()
        source.fetch_jobs.return_value = []

        result = visitor.visit_search_engine(source)
        assert result == []

    def test_accept_routes_to_visit_search_engine(self):
        visitor = MagicMock()
        visitor.visit_search_engine.return_value = []
        source = LinkedInSource()
        source.accept(visitor)
        visitor.visit_search_engine.assert_called_once_with(source)

    def test_visit_company_site_delegates(self):
        visitor = ScrapingVisitor()
        source = MagicMock()
        source.fetch_jobs.return_value = []
        result = visitor.visit_company_site(source)
        source.fetch_jobs.assert_called_once()
        assert result == []

    def test_visit_ats_platform_delegates(self):
        visitor = ScrapingVisitor()
        source = MagicMock()
        source.fetch_jobs.return_value = []
        result = visitor.visit_ats_platform(source)
        source.fetch_jobs.assert_called_once()
        assert result == []
