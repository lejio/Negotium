"""Tests for job source classes — URL building, naming, and HTML parsing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from negotium.config import ExperienceLevel, PostedWithin, SearchConfig
from negotium.models.job import Job
from negotium.sources.base import ATSPlatform, CompanyWebsite, JobSearchEngine, JobSource
from negotium.sources.search_engines.glassdoor import GlassdoorSource
from negotium.sources.search_engines.indeed import IndeedSource
from negotium.sources.search_engines.linkedin import LinkedInSource
from negotium.sources.search_engines.ziprecruiter import ZipRecruiterSource


# ─── Base class tests ────────────────────────────────────────────────────────


class TestJobSourceBase:
    """Test the abstract base classes and visitor dispatch."""

    def test_search_engine_dispatches_to_visit_search_engine(self):
        source = LinkedInSource()
        visitor = MagicMock()
        visitor.visit_search_engine.return_value = []
        source.accept(visitor)
        visitor.visit_search_engine.assert_called_once_with(source)

    def test_default_headers(self):
        source = LinkedInSource()
        headers = source.headers
        assert "User-Agent" in headers
        assert "Mozilla" in headers["User-Agent"]

    def test_all_search_engines_are_job_sources(self):
        for cls in [LinkedInSource, IndeedSource, ZipRecruiterSource, GlassdoorSource]:
            source = cls()
            assert isinstance(source, JobSource)
            assert isinstance(source, JobSearchEngine)


# ─── LinkedIn ────────────────────────────────────────────────────────────────


class TestLinkedInSource:
    """Test LinkedIn source URL building and HTML parsing."""

    def test_default_name(self):
        source = LinkedInSource()
        assert "LinkedIn" in source.name
        assert "software engineer" in source.name

    def test_name_with_location(self):
        source = LinkedInSource(
            search=SearchConfig(keywords="swe", location="NYC")
        )
        assert "NYC" in source.name

    def test_build_url_contains_keywords(self):
        source = LinkedInSource(search=SearchConfig(keywords="python"))
        url = source._build_url()
        assert "keywords=python" in url

    def test_build_url_sort_by_date(self):
        source = LinkedInSource()
        url = source._build_url()
        assert "sortBy=DD" in url

    def test_build_url_experience_level(self):
        source = LinkedInSource(
            search=SearchConfig(experience_levels=[ExperienceLevel.ENTRY_LEVEL])
        )
        url = source._build_url()
        assert "f_E=2" in url

    def test_build_url_multiple_experience_levels(self):
        source = LinkedInSource(
            search=SearchConfig(
                experience_levels=[ExperienceLevel.ENTRY_LEVEL, ExperienceLevel.MID_SENIOR]
            )
        )
        url = source._build_url()
        assert "f_E=2%2C4" in url or "f_E=2,4" in url

    def test_build_url_time_filter(self):
        source = LinkedInSource(
            search=SearchConfig(posted_within=PostedWithin.PAST_WEEK)
        )
        url = source._build_url()
        assert "f_TPR=r604800" in url

    def test_build_url_location(self):
        source = LinkedInSource(
            search=SearchConfig(location="San Francisco")
        )
        url = source._build_url()
        assert "location=" in url
        assert "San" in url

    def test_build_url_remote(self):
        source = LinkedInSource(search=SearchConfig(remote_only=True))
        url = source._build_url()
        assert "f_WT=2" in url

    def test_build_url_pagination(self):
        source = LinkedInSource()
        url = source._build_url(start=25)
        assert "start=25" in url

    def test_fetch_jobs_parses_html(self):
        """Test that fetch_jobs correctly parses LinkedIn HTML cards."""
        html = """
        <div class="base-card">
            <h3 class="base-search-card__title">Software Engineer</h3>
            <a class="base-card__full-link" href="https://linkedin.com/jobs/view/123?trk=foo">View</a>
            <h4 class="base-search-card__subtitle">Acme Corp</h4>
            <span class="job-search-card__location">San Francisco, CA</span>
            <time>2 hours ago</time>
        </div>
        """
        source = LinkedInSource(max_pages=1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html

        with patch("negotium.sources.search_engines.linkedin.requests.get", return_value=mock_resp):
            jobs = source.fetch_jobs()

        assert len(jobs) == 1
        assert jobs[0].title == "Software Engineer"
        assert jobs[0].company == "Acme Corp"
        assert jobs[0].location == "San Francisco, CA"
        assert "123" in jobs[0].link
        assert "?" not in jobs[0].link  # tracking params stripped
        assert jobs[0].posted == "2 hours ago"

    def test_fetch_jobs_handles_http_error(self):
        source = LinkedInSource(max_pages=1)
        mock_resp = MagicMock()
        mock_resp.status_code = 429

        with patch("negotium.sources.search_engines.linkedin.requests.get", return_value=mock_resp):
            jobs = source.fetch_jobs()

        assert jobs == []

    def test_fetch_jobs_handles_request_exception(self):
        source = LinkedInSource(max_pages=1)
        import requests
        with patch(
            "negotium.sources.search_engines.linkedin.requests.get",
            side_effect=requests.RequestException("timeout"),
        ):
            jobs = source.fetch_jobs()

        assert jobs == []

    def test_fetch_jobs_empty_html(self):
        source = LinkedInSource(max_pages=1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body></body></html>"

        with patch("negotium.sources.search_engines.linkedin.requests.get", return_value=mock_resp):
            jobs = source.fetch_jobs()

        assert jobs == []


# ─── Indeed ──────────────────────────────────────────────────────────────────


class TestIndeedSource:
    """Test Indeed source URL building and parsing."""

    def test_name(self):
        source = IndeedSource(search=SearchConfig(keywords="data analyst", location="Boston"))
        assert "Indeed" in source.name
        assert "data analyst" in source.name
        assert "Boston" in source.name

    def test_build_url_keywords(self):
        source = IndeedSource(search=SearchConfig(keywords="react"))
        url = source._build_url()
        assert "q=react" in url

    def test_build_url_sort_date(self):
        source = IndeedSource()
        url = source._build_url()
        assert "sort=date" in url

    def test_build_url_location(self):
        source = IndeedSource(search=SearchConfig(location="Chicago"))
        url = source._build_url()
        assert "l=Chicago" in url

    def test_build_url_fromage(self):
        source = IndeedSource(search=SearchConfig(posted_within=PostedWithin.PAST_WEEK))
        url = source._build_url()
        assert "fromage=7" in url

    def test_build_url_experience_level(self):
        source = IndeedSource(
            search=SearchConfig(experience_levels=[ExperienceLevel.ENTRY_LEVEL])
        )
        url = source._build_url()
        assert "ENTRY_LEVEL" in url

    def test_build_url_remote(self):
        source = IndeedSource(search=SearchConfig(remote_only=True))
        url = source._build_url()
        assert "remotejob" in url

    def test_fetch_jobs_parses_html(self):
        html = """
        <div class="job_seen_beacon">
            <h2 class="jobTitle">Data Analyst</h2>
            <a href="/viewjob?jk=abc123&tk=xyz">Apply</a>
            <span data-testid="company-name">DataCo</span>
            <div data-testid="text-location">Remote</div>
            <span class="date">Posted 1 day ago</span>
        </div>
        """
        source = IndeedSource(max_pages=1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html

        with patch("negotium.sources.search_engines.indeed.requests.get", return_value=mock_resp):
            jobs = source.fetch_jobs()

        assert len(jobs) == 1
        assert jobs[0].title == "Data Analyst"
        assert jobs[0].company == "DataCo"
        assert "indeed.com" in jobs[0].link


# ─── ZipRecruiter ────────────────────────────────────────────────────────────


class TestZipRecruiterSource:
    """Test ZipRecruiter source URL building and parsing."""

    def test_name(self):
        source = ZipRecruiterSource(search=SearchConfig(keywords="devops"))
        assert "ZipRecruiter" in source.name
        assert "devops" in source.name

    def test_build_url_keywords(self):
        source = ZipRecruiterSource(search=SearchConfig(keywords="go developer"))
        url = source._build_url()
        assert "search=go" in url

    def test_build_url_location(self):
        source = ZipRecruiterSource(search=SearchConfig(location="Denver"))
        url = source._build_url()
        assert "location=Denver" in url

    def test_build_url_days(self):
        source = ZipRecruiterSource(
            search=SearchConfig(posted_within=PostedWithin.PAST_MONTH)
        )
        url = source._build_url()
        assert "days=30" in url

    def test_build_url_remote(self):
        source = ZipRecruiterSource(search=SearchConfig(remote_only=True))
        url = source._build_url()
        assert "remote" in url

    def test_build_url_pagination(self):
        source = ZipRecruiterSource()
        url = source._build_url(page=3)
        assert "page=3" in url

    def test_fetch_jobs_parses_html(self):
        html = """
        <article class="job_result">
            <h2 class="job_title">DevOps Engineer</h2>
            <a href="https://www.ziprecruiter.com/jobs/devops-1?mid=x">Apply</a>
            <a class="company_name">CloudInc</a>
            <span class="location">Seattle, WA</span>
            <span class="posted">Today</span>
        </article>
        """
        source = ZipRecruiterSource(max_pages=1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html

        with patch("negotium.sources.search_engines.ziprecruiter.requests.get", return_value=mock_resp):
            jobs = source.fetch_jobs()

        assert len(jobs) == 1
        assert jobs[0].title == "DevOps Engineer"
        assert jobs[0].company == "CloudInc"


# ─── Glassdoor ───────────────────────────────────────────────────────────────


class TestGlassdoorSource:
    """Test Glassdoor source URL building and parsing."""

    def test_name(self):
        source = GlassdoorSource(search=SearchConfig(keywords="ml engineer", location="Seattle"))
        assert "Glassdoor" in source.name
        assert "ml engineer" in source.name
        assert "Seattle" in source.name

    def test_build_url_keywords(self):
        source = GlassdoorSource(search=SearchConfig(keywords="frontend"))
        url = source._build_url()
        assert "sc.keyword=frontend" in url

    def test_build_url_sort_by_date(self):
        source = GlassdoorSource()
        url = source._build_url()
        assert "sortBy=date" in url

    def test_build_url_location(self):
        source = GlassdoorSource(search=SearchConfig(location="LA"))
        url = source._build_url()
        assert "locKeyword=LA" in url

    def test_build_url_seniority(self):
        source = GlassdoorSource(
            search=SearchConfig(experience_levels=[ExperienceLevel.ENTRY_LEVEL])
        )
        url = source._build_url()
        assert "seniorityType=entrylevel" in url

    def test_build_url_fromage(self):
        source = GlassdoorSource(
            search=SearchConfig(posted_within=PostedWithin.PAST_MONTH)
        )
        url = source._build_url()
        assert "fromAge=30" in url

    def test_build_url_remote(self):
        source = GlassdoorSource(search=SearchConfig(remote_only=True))
        url = source._build_url()
        assert "remoteWorkType" in url

    def test_custom_headers(self):
        source = GlassdoorSource()
        headers = source.headers
        assert "Referer" in headers
        assert "glassdoor.com" in headers["Referer"]

    def test_build_url_pagination(self):
        source = GlassdoorSource()
        url_p1 = source._build_url(page=1)
        url_p2 = source._build_url(page=2)
        assert "p=" not in url_p1  # page 1 omits p param
        assert "p=2" in url_p2
