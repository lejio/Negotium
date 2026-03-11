"""
Shared Selenium WebDriver factory.

Provides two driver modes:

1. ``make_driver()`` – standard headless Chrome with basic stealth flags.
   Good enough for most job boards (Glassdoor, Dice, FlexJobs, etc.).

2. ``make_undetected_driver()`` – uses the *undetected-chromedriver* package
   which patches the Chrome binary to remove automation fingerprints.
   Required for aggressive anti-bot sites like **Indeed**.
"""

from __future__ import annotations

import os
import shutil

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


# ---------------------------------------------------------------------------
# Browser / driver discovery helpers
# ---------------------------------------------------------------------------

def _find_browser() -> str | None:
    """Locate Chrome/Chromium binary, including snap installs."""
    for name in (
        "google-chrome",
        "chromium-browser",
        "chromium",
    ):
        path = shutil.which(name)
        if path:
            return path
    # Snap installs may not be on PATH
    snap_path = "/snap/bin/chromium"
    try:
        if os.path.isfile(snap_path) and os.access(snap_path, os.X_OK):
            return snap_path
    except OSError:
        pass
    return None


def _find_chromedriver() -> str | None:
    """Locate chromedriver binary."""
    path = shutil.which("chromedriver")
    if path:
        return path
    for candidate in ("/usr/bin/chromedriver", "/usr/local/bin/chromedriver"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


# ---------------------------------------------------------------------------
# Standard headless driver (basic stealth)
# ---------------------------------------------------------------------------

def make_driver() -> webdriver.Chrome:
    """Create a headless Chrome/Chromium driver with stealth settings."""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    # Disable automation flags that sites detect
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    # Locate browser binary (handles snap installs not on PATH)
    browser_path = _find_browser()
    if browser_path:
        opts.binary_location = browser_path

    # Locate chromedriver
    service_kwargs: dict = {}
    chromedriver_path = _find_chromedriver()
    if chromedriver_path:
        service_kwargs["executable_path"] = chromedriver_path

    driver = webdriver.Chrome(
        options=opts,
        service=Service(**service_kwargs),
    )

    # Remove webdriver navigator flag
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


# ---------------------------------------------------------------------------
# Undetected driver (binary-patched Chrome – for aggressive anti-bot sites)
# ---------------------------------------------------------------------------

def make_undetected_driver() -> webdriver.Chrome:
    """Create a headless Chrome driver using *undetected-chromedriver*.

    This patches the Chrome binary itself to remove automation markers
    that sites like Indeed detect.  Falls back to :func:`make_driver` if
    the ``undetected_chromedriver`` package is not installed.
    """
    try:
        import undetected_chromedriver as uc  # type: ignore[import-untyped]
    except ImportError:
        print(
            "  [!] undetected-chromedriver not installed – "
            "falling back to standard driver"
        )
        return make_driver()

    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    browser_path = _find_browser()
    if browser_path:
        options.binary_location = browser_path

    # Detect installed browser version so UC downloads a matching chromedriver
    version_main = _detect_browser_major_version(browser_path)

    driver = uc.Chrome(
        options=options,
        headless=True,
        version_main=version_main,
    )
    return driver


def _detect_browser_major_version(browser_path: str | None) -> int | None:
    """Return the major version of the installed Chrome/Chromium, or None."""
    import subprocess

    path = browser_path or _find_browser()
    if not path:
        return None
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Output looks like: "Chromium 145.0.7632.116 snap" or "Google Chrome 131.0.xxxx"
        for token in result.stdout.split():
            if "." in token:
                return int(token.split(".")[0])
    except Exception:
        pass
    return None
