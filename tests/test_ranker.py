"""Tests for negotium.ranker — LLM job ranking."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from negotium.config import LLMConfig
from negotium.models.job import Job
from negotium.ranker import _build_job_text, _load_resume, rank_job, rank_jobs


class TestBuildJobText:
    """Test helper that formats a job into LLM-friendly text."""

    def test_contains_all_fields(self, sample_job):
        text = _build_job_text(sample_job)
        assert "Software Engineer" in text
        assert "Acme Corp" in text
        assert "San Francisco, CA" in text
        assert "2 hours ago" in text
        assert "example.com" in text

    def test_format_structure(self, sample_job):
        text = _build_job_text(sample_job)
        assert text.startswith("Title:")
        assert "Company:" in text
        assert "Location:" in text
        assert "Posted:" in text
        assert "Link:" in text


class TestLoadResume:
    """Test resume file loading."""

    def test_loads_existing_resume(self, tmp_path):
        resume = tmp_path / "resume.txt"
        resume.write_text("I am a developer.")
        config = LLMConfig(resume_path=resume)
        result = _load_resume(config)
        assert result == "I am a developer."

    def test_returns_empty_when_missing(self, tmp_path):
        config = LLMConfig(resume_path=tmp_path / "nonexistent.txt")
        result = _load_resume(config)
        assert result == ""


class TestRankJob:
    """Test single-job ranking with mocked LLM."""

    def test_returns_score_from_openai(self, sample_job, llm_config):
        with patch("negotium.ranker._call_openai", return_value="75"):
            resume_text = "Experienced Python developer."
            score = rank_job(sample_job, llm_config, resume_text)
        assert score == 75

    def test_returns_score_from_local(self, sample_job, tmp_path):
        resume = tmp_path / "resume.txt"
        resume.write_text("dev")
        config = LLMConfig(enabled=True, provider="local", resume_path=resume)
        with patch("negotium.ranker._call_local", return_value="  42  "):
            score = rank_job(sample_job, config, "dev")
        assert score == 42

    def test_clamps_score_to_0_100(self, sample_job, llm_config):
        with patch("negotium.ranker._call_openai", return_value="150"):
            score = rank_job(sample_job, llm_config, "resume text")
        assert score == 100

    def test_clamps_negative_score(self, sample_job, llm_config):
        with patch("negotium.ranker._call_openai", return_value="-10"):
            score = rank_job(sample_job, llm_config, "resume text")
        assert score == 0

    def test_returns_minus1_on_exception(self, sample_job, llm_config):
        with patch("negotium.ranker._call_openai", side_effect=Exception("API error")):
            score = rank_job(sample_job, llm_config, "resume text")
        assert score == -1

    def test_returns_minus1_on_empty_resume(self, sample_job, llm_config):
        score = rank_job(sample_job, llm_config, "")
        assert score == -1

    def test_returns_minus1_on_non_numeric(self, sample_job, llm_config):
        with patch("negotium.ranker._call_openai", return_value="great match!"):
            score = rank_job(sample_job, llm_config, "resume text")
        assert score == -1


class TestRankJobs:
    """Test batch ranking with mocked LLM."""

    def test_returns_unmodified_when_disabled(self, sample_jobs, disabled_llm_config):
        result = rank_jobs(sample_jobs, disabled_llm_config)
        assert result == sample_jobs
        assert all(j.match_score is None for j in result)

    def test_scores_all_jobs(self, sample_jobs, llm_config):
        scores = iter(["80", "60", "90"])
        with patch("negotium.ranker._call_openai", side_effect=scores):
            result = rank_jobs(sample_jobs, llm_config)

        assert all(j.match_score is not None for j in result)
        # Should be sorted descending by score
        assert result[0].match_score >= result[1].match_score >= result[2].match_score

    def test_returns_unmodified_when_no_resume(self, sample_jobs, tmp_path):
        config = LLMConfig(
            enabled=True,
            resume_path=tmp_path / "nonexistent.txt",
        )
        result = rank_jobs(sample_jobs, config)
        assert all(j.match_score is None for j in result)
