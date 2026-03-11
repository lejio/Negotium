"""Tests for the Firecrawl client and FirecrawlVisitor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from negotium.firecrawl_client import scrape_page
from negotium.models.job import Job
from negotium.visitors.firecrawl import FirecrawlVisitor


# ─── Firecrawl client tests ─────────────────────────────────────────────────


class TestScrapePageClient:
    """Test the low-level Firecrawl HTTP wrapper."""

    @patch("negotium.firecrawl_client.requests.post")
    def test_returns_raw_html_on_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "success": True,
            "data": {"rawHtml": "<html><body>hello</body></html>"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = scrape_page("https://example.com", api_url="http://localhost:3002")

        assert result == "<html><body>hello</body></html>"
        mock_post.assert_called_once_with(
            "http://localhost:3002/v1/scrape",
            json={"url": "https://example.com", "formats": ["rawHtml"]},
            timeout=60,
        )

    @patch("negotium.firecrawl_client.requests.post")
    def test_returns_none_on_failure_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": False}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = scrape_page("https://example.com")
        assert result is None

    @patch("negotium.firecrawl_client.requests.post")
    def test_returns_none_on_request_exception(self, mock_post):
        import requests

        mock_post.side_effect = requests.ConnectionError("refused")

        result = scrape_page("https://example.com")
        assert result is None

    @patch("negotium.firecrawl_client.requests.post")
    def test_returns_none_on_invalid_json(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.side_effect = ValueError("bad json")
        mock_post.return_value = mock_resp

        result = scrape_page("https://example.com")
        assert result is None

    @patch("negotium.firecrawl_client.requests.post")
    def test_strips_trailing_slash_from_api_url(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "data": {"rawHtml": "<html/>"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        scrape_page("https://example.com", api_url="http://localhost:3002/")

        call_url = mock_post.call_args[0][0]
        assert call_url == "http://localhost:3002/v1/scrape"

    @patch("negotium.firecrawl_client.requests.post")
    def test_custom_timeout(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "data": {"rawHtml": ""}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        scrape_page("https://example.com", timeout=120)

        assert mock_post.call_args[1]["timeout"] == 120


# ─── FirecrawlVisitor tests ─────────────────────────────────────────────────


class TestFirecrawlVisitor:
    """Test FirecrawlVisitor dispatch and fallback logic."""

    def test_init_stores_api_url(self):
        v = FirecrawlVisitor(api_url="http://my-server:4000")
        assert v.api_url == "http://my-server:4000"

    def test_supports_firecrawl_true(self):
        source = MagicMock()
        source.build_page_urls = MagicMock(return_value=[])
        source.parse_page = MagicMock(return_value=[])
        v = FirecrawlVisitor()
        assert v._supports_firecrawl(source) is True

    def test_supports_firecrawl_false(self):
        source = MagicMock(spec=["fetch_jobs", "name"])
        v = FirecrawlVisitor()
        assert v._supports_firecrawl(source) is False

    @patch("negotium.visitors.firecrawl.scrape_page")
    def test_visit_search_engine_uses_firecrawl(self, mock_scrape):
        """Sources with build_page_urls + parse_page are fetched via Firecrawl."""
        html = "<html><body>jobs</body></html>"
        mock_scrape.return_value = html

        job = Job(
            title="SE", company="Co", location="Remote",
            link="https://x.com/1", posted="now",
        )
        source = MagicMock()
        source.build_page_urls.return_value = ["https://site.com/jobs?page=1"]
        source.parse_page.return_value = [job]

        v = FirecrawlVisitor(api_url="http://localhost:3002")
        result = v.visit_search_engine(source)

        assert result == [job]
        mock_scrape.assert_called_once_with("https://site.com/jobs?page=1", "http://localhost:3002")
        source.parse_page.assert_called_once_with(html)

    @patch("negotium.visitors.firecrawl.scrape_page")
    def test_visit_search_engine_multiple_pages(self, mock_scrape):
        html1 = "<html>page1</html>"
        html2 = "<html>page2</html>"
        mock_scrape.side_effect = [html1, html2]

        job1 = Job(title="J1", company="C", location="L", link="https://x.com/1", posted="now")
        job2 = Job(title="J2", company="C", location="L", link="https://x.com/2", posted="now")
        source = MagicMock()
        source.build_page_urls.return_value = [
            "https://site.com/jobs?page=1",
            "https://site.com/jobs?page=2",
        ]
        source.parse_page.side_effect = [[job1], [job2]]

        v = FirecrawlVisitor()
        result = v.visit_search_engine(source)

        assert len(result) == 2
        assert result[0].title == "J1"
        assert result[1].title == "J2"

    @patch("negotium.visitors.firecrawl.scrape_page")
    def test_stops_on_empty_page(self, mock_scrape):
        """Pagination stops when a page returns no jobs."""
        mock_scrape.return_value = "<html></html>"

        source = MagicMock()
        source.build_page_urls.return_value = [
            "https://site.com/jobs?page=1",
            "https://site.com/jobs?page=2",
        ]
        source.parse_page.return_value = []  # no jobs found

        v = FirecrawlVisitor()
        result = v.visit_search_engine(source)

        assert result == []
        # Should stop after first empty page, not fetch page 2
        assert mock_scrape.call_count == 1

    @patch("negotium.visitors.firecrawl.scrape_page")
    def test_continues_on_firecrawl_failure(self, mock_scrape):
        """If Firecrawl fails for one page, try the next."""
        html = "<html>page2</html>"
        mock_scrape.side_effect = [None, html]

        job = Job(title="J", company="C", location="L", link="https://x.com/1", posted="now")
        source = MagicMock()
        source.build_page_urls.return_value = ["url1", "url2"]
        source.parse_page.return_value = [job]

        v = FirecrawlVisitor()
        result = v.visit_search_engine(source)

        assert len(result) == 1
        assert mock_scrape.call_count == 2

    def test_falls_back_to_fetch_jobs_for_unsupported_source(self):
        """Sources without build_page_urls fall back to fetch_jobs()."""
        job = Job(title="T", company="C", location="L", link="https://x.com/1", posted="now")
        source = MagicMock(spec=["fetch_jobs", "name"])
        source.fetch_jobs.return_value = [job]

        v = FirecrawlVisitor()
        result = v.visit_search_engine(source)

        assert result == [job]
        source.fetch_jobs.assert_called_once()

    @patch("negotium.visitors.firecrawl.scrape_page")
    def test_visit_company_site_uses_firecrawl(self, mock_scrape):
        mock_scrape.return_value = "<html/>"
        source = MagicMock()
        source.build_page_urls.return_value = ["url1"]
        source.parse_page.return_value = []

        v = FirecrawlVisitor()
        v.visit_company_site(source)

        mock_scrape.assert_called_once()

    @patch("negotium.visitors.firecrawl.scrape_page")
    def test_visit_ats_platform_uses_firecrawl(self, mock_scrape):
        mock_scrape.return_value = "<html/>"
        source = MagicMock()
        source.build_page_urls.return_value = ["url1"]
        source.parse_page.return_value = []

        v = FirecrawlVisitor()
        v.visit_ats_platform(source)

        mock_scrape.assert_called_once()

    def test_visit_company_site_fallback(self):
        source = MagicMock(spec=["fetch_jobs"])
        source.fetch_jobs.return_value = []
        v = FirecrawlVisitor()
        v.visit_company_site(source)
        source.fetch_jobs.assert_called_once()

    def test_visit_ats_platform_fallback(self):
        source = MagicMock(spec=["fetch_jobs"])
        source.fetch_jobs.return_value = []
        v = FirecrawlVisitor()
        v.visit_ats_platform(source)
        source.fetch_jobs.assert_called_once()


# ─── Source parse_page / build_page_urls tests ───────────────────────────────


class TestSourceFirecrawlInterface:
    """Test that refactored sources expose build_page_urls and parse_page."""

    def test_ziprecruiter_build_page_urls(self):
        from negotium.sources.search_engines.ziprecruiter import ZipRecruiterSource

        source = ZipRecruiterSource(max_pages=3)
        urls = source.build_page_urls()
        assert len(urls) == 3
        assert "page=1" in urls[0]
        assert "page=2" in urls[1]
        assert "page=3" in urls[2]

    def test_ziprecruiter_parse_page(self):
        from negotium.sources.search_engines.ziprecruiter import ZipRecruiterSource

        html = """
        <script type="application/ld+json">
        {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": "1",
             "url": "https://www.ziprecruiter.com/c/Co/Job/-in-NYC?jid=x"}
        ]}
        </script>
        <div class="job_result_two_pane_v2">
            <article>
                <h2>DevOps Engineer</h2>
                <a data-testid="job-card-company">CloudInc</a>
                <a data-testid="job-card-location">Seattle, WA</a>
            </article>
        </div>
        """
        source = ZipRecruiterSource()
        jobs = source.parse_page(html)
        assert len(jobs) == 1
        assert jobs[0].title == "DevOps Engineer"
        assert jobs[0].company == "CloudInc"
        assert "ziprecruiter.com" in jobs[0].link

    def test_indeed_build_page_urls(self):
        from negotium.sources.search_engines.indeed import IndeedSource

        source = IndeedSource(max_pages=2)
        urls = source.build_page_urls()
        assert len(urls) == 2
        assert "start=0" in urls[0]
        assert "start=10" in urls[1]

    def test_indeed_parse_page(self):
        from negotium.sources.search_engines.indeed import IndeedSource

        html = """
        <div class="job_seen_beacon">
            <h2 class="jobTitle">Data Analyst</h2>
            <a href="/viewjob?jk=abc123">Apply</a>
            <span data-testid="company-name">DataCo</span>
            <div data-testid="text-location">Remote</div>
            <span class="date">1 day ago</span>
        </div>
        """
        source = IndeedSource()
        jobs = source.parse_page(html)
        assert len(jobs) == 1
        assert jobs[0].title == "Data Analyst"
        assert jobs[0].company == "DataCo"
        assert "indeed.com" in jobs[0].link

    def test_indeed_parse_page_detects_block(self):
        from negotium.sources.search_engines.indeed import IndeedSource

        html = "<html><head><title>Blocked</title></head><body></body></html>"
        source = IndeedSource()
        jobs = source.parse_page(html)
        assert jobs == []

    def test_glassdoor_build_page_urls(self):
        from negotium.sources.search_engines.glassdoor import GlassdoorSource

        source = GlassdoorSource(max_pages=2)
        urls = source.build_page_urls()
        assert len(urls) == 2

    def test_glassdoor_parse_page(self):
        from negotium.sources.search_engines.glassdoor import GlassdoorSource

        html = """
        <li data-test="jobListing">
            <a data-test="job-title" href="/job-listing/se-123.htm?extra=1">
                Software Engineer
            </a>
            <div data-test="emp-name">TechCo</div>
            <span data-test="emp-location">Remote</span>
            <div data-test="job-age">2d</div>
        </li>
        """
        source = GlassdoorSource()
        jobs = source.parse_page(html)
        assert len(jobs) == 1
        assert jobs[0].title == "Software Engineer"
        assert "glassdoor.com" in jobs[0].link
        assert "?" not in jobs[0].link  # query params stripped

    def test_glassdoor_parse_page_empty(self):
        from negotium.sources.search_engines.glassdoor import GlassdoorSource

        html = "<html><body>No jobs</body></html>"
        source = GlassdoorSource()
        jobs = source.parse_page(html)
        assert jobs == []
