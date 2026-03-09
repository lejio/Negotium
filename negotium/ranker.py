"""
LLM-based job ranking.

Reads a job posting and compares it against a resume / profile to
produce a match score from 0 to 100.

Currently supports OpenAI.  Additional providers (Anthropic, local
models) can be added by extending the ``_call_llm`` method or
swapping in a different client.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from negotium.config import LLMConfig
    from negotium.models.job import Job

SYSTEM_PROMPT = """\
You are a career-matching assistant.  You will receive a candidate's resume
and a job listing.  Score how well the candidate matches the job on a scale
of 0 to 100, where:

  0   = completely unrelated
  50  = some overlap but missing key requirements
  100 = perfect match

Respond with ONLY a single integer (the score).  No explanation."""


def _build_job_text(job: "Job") -> str:
    """Flatten a Job into a readable text block for the LLM."""
    return (
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Location: {job.location}\n"
        f"Posted: {job.posted}\n"
        f"Link: {job.link}\n"
    )


def _load_resume(config: "LLMConfig") -> str:
    """Load the resume text from disk."""
    path = config.resume_path
    if not path.exists():
        print(f"  [!] Resume file not found: {path}")
        return ""
    return path.read_text(encoding="utf-8")


def rank_job(job: "Job", config: "LLMConfig", resume_text: str) -> int:
    """
    Call the LLM to score a job against the resume.

    Routes to the correct provider based on ``config.provider``.
    Returns an integer 0-100, or -1 on failure.
    """
    if not resume_text:
        return -1

    job_text = _build_job_text(job)
    user_prompt = (
        f"=== RESUME ===\n{resume_text}\n\n"
        f"=== JOB LISTING ===\n{job_text}"
    )

    try:
        if config.provider == "local":
            score_str = _call_local(config, user_prompt)
        else:
            score_str = _call_openai(config, user_prompt)
        score = int(score_str.strip())
        return max(0, min(100, score))
    except Exception as exc:
        print(f"  [!] LLM ranking failed for '{job.title}': {exc}")
        return -1


def _call_openai(config: "LLMConfig", user_prompt: str) -> str:
    """Call OpenAI chat completion and return the raw response text."""
    from openai import OpenAI

    api_key = config.api_key or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("No OpenAI API key configured")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=config.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=10,
    )
    return response.choices[0].message.content or ""


def _call_local(config: "LLMConfig", user_prompt: str) -> str:
    """
    Call a locally-running LLM via the OpenAI-compatible API.

    Works with any server that exposes ``/v1/chat/completions``:
      - Ollama          (default: http://localhost:11434/v1)
      - LM Studio       (default: http://localhost:1234/v1)
      - llama.cpp server(default: http://localhost:8080/v1)
      - vLLM            (default: http://localhost:8000/v1)
      - LocalAI, Jan, etc.

    Set ``config.base_url`` to the server's base URL and
    ``config.model`` to the model name loaded on that server.
    """
    from openai import OpenAI

    client = OpenAI(
        base_url=config.base_url,
        api_key=config.api_key or "not-needed",  # local servers usually ignore this
    )
    response = client.chat.completions.create(
        model=config.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=10,
    )
    return response.choices[0].message.content or ""


def rank_jobs(
    jobs: list["Job"],
    config: "LLMConfig",
) -> list["Job"]:
    """
    Score a batch of jobs against the resume.

    Mutates each job's ``match_score`` in place and returns the list
    sorted by score (highest first).  Jobs below
    ``config.min_score_to_notify`` are still returned but can be
    filtered downstream.
    """
    if not config.enabled:
        return jobs

    resume_text = _load_resume(config)
    if not resume_text:
        return jobs

    for job in jobs:
        job.match_score = rank_job(job, config, resume_text)

    # Sort by score descending; jobs that failed (-1) go to the end
    jobs.sort(key=lambda j: j.match_score if j.match_score >= 0 else -1, reverse=True)
    return jobs
