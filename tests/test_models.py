"""Tests for negotium.models.job — the Job dataclass."""

from __future__ import annotations

import hashlib

from negotium.models.job import Job


class TestJobCreation:
    """Test Job dataclass instantiation and defaults."""

    def test_minimal_creation(self):
        job = Job(
            title="SWE",
            company="Corp",
            location="NYC",
            link="https://example.com/1",
            posted="1h ago",
        )
        assert job.title == "SWE"
        assert job.company == "Corp"
        assert job.source == ""
        assert job.match_score is None

    def test_auto_job_id_from_link(self):
        link = "https://example.com/jobs/42"
        job = Job(title="T", company="C", location="L", link=link, posted="now")
        expected = hashlib.md5(link.encode()).hexdigest()
        assert job.job_id == expected

    def test_explicit_job_id_preserved(self):
        job = Job(
            title="T", company="C", location="L",
            link="https://example.com/1", posted="now",
            job_id="custom-id-123",
        )
        assert job.job_id == "custom-id-123"

    def test_empty_link_no_auto_id(self):
        job = Job(title="T", company="C", location="L", link="", posted="now")
        assert job.job_id == ""

    def test_match_score_default_none(self, sample_job):
        assert sample_job.match_score is None

    def test_match_score_settable(self, sample_job):
        sample_job.match_score = 85
        assert sample_job.match_score == 85


class TestJobEquality:
    """Test that jobs with different links get different IDs."""

    def test_different_links_different_ids(self):
        job_a = Job(title="T", company="C", location="L", link="https://a.com/1", posted="now")
        job_b = Job(title="T", company="C", location="L", link="https://a.com/2", posted="now")
        assert job_a.job_id != job_b.job_id

    def test_same_link_same_id(self):
        job_a = Job(title="A", company="X", location="L", link="https://a.com/1", posted="now")
        job_b = Job(title="B", company="Y", location="L", link="https://a.com/1", posted="later")
        assert job_a.job_id == job_b.job_id
