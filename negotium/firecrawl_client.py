"""Lightweight client for the self-hosted Firecrawl scraping API.

Firecrawl renders pages with Playwright under the hood, making it a
drop-in replacement for Selenium-based fetching with better anti-bot
resilience.

Usage::

    html = scrape_page("https://example.com", api_url="http://localhost:3002")
"""

from __future__ import annotations

import requests


def scrape_page(
    url: str,
    api_url: str = "http://localhost:3002",
    timeout: int = 60,
) -> str | None:
    """Fetch a page via the Firecrawl API and return its raw HTML.

    Parameters
    ----------
    url:
        The page URL to scrape.
    api_url:
        Base URL of the self-hosted Firecrawl instance.
    timeout:
        HTTP request timeout in seconds.

    Returns
    -------
    str | None
        The raw HTML of the rendered page, or ``None`` on failure.
    """
    try:
        resp = requests.post(
            f"{api_url.rstrip('/')}/v1/scrape",
            json={"url": url, "formats": ["rawHtml"]},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            return data.get("data", {}).get("rawHtml")
        print(f"  [!] Firecrawl returned success=false for {url}")
    except requests.RequestException as exc:
        print(f"  [!] Firecrawl request failed: {exc}")
    except (ValueError, KeyError) as exc:
        print(f"  [!] Firecrawl response parse error: {exc}")
    return None
