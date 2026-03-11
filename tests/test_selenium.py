"""Tests for Selenium WebDriver setup and Chromium integration.

These tests verify:
  • The shared driver factory produces a valid Chrome driver
  • Driver anti-detection settings are applied
  • All Selenium-based scrapers create and quit drivers properly
  • Driver failure is handled gracefully
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch




# ─── Driver factory tests ────────────────────────────────────────────────────


class TestMakeDriver:
    """Test the shared make_driver factory in negotium.sources.driver."""

    @patch("negotium.sources.driver.webdriver.Chrome")
    def test_returns_chrome_driver(self, mock_chrome_cls):
        from negotium.sources.driver import make_driver

        mock_driver = MagicMock()
        mock_chrome_cls.return_value = mock_driver

        driver = make_driver()

        assert driver is mock_driver
        mock_chrome_cls.assert_called_once()

    @patch("negotium.sources.driver.webdriver.Chrome")
    def test_sets_headless_mode(self, mock_chrome_cls):
        from negotium.sources.driver import make_driver

        mock_driver = MagicMock()
        mock_chrome_cls.return_value = mock_driver

        make_driver()

        # Inspect the Options object passed to Chrome()
        opts = mock_chrome_cls.call_args[1]["options"]
        args = opts.arguments
        assert "--headless=new" in args

    @patch("negotium.sources.driver.webdriver.Chrome")
    def test_sets_no_sandbox(self, mock_chrome_cls):
        from negotium.sources.driver import make_driver

        mock_driver = MagicMock()
        mock_chrome_cls.return_value = mock_driver

        make_driver()

        opts = mock_chrome_cls.call_args[1]["options"]
        args = opts.arguments
        assert "--no-sandbox" in args

    @patch("negotium.sources.driver.webdriver.Chrome")
    def test_sets_disable_dev_shm(self, mock_chrome_cls):
        from negotium.sources.driver import make_driver

        mock_driver = MagicMock()
        mock_chrome_cls.return_value = mock_driver

        make_driver()

        opts = mock_chrome_cls.call_args[1]["options"]
        args = opts.arguments
        assert "--disable-dev-shm-usage" in args

    @patch("negotium.sources.driver.webdriver.Chrome")
    def test_sets_custom_user_agent(self, mock_chrome_cls):
        from negotium.sources.driver import make_driver

        mock_driver = MagicMock()
        mock_chrome_cls.return_value = mock_driver

        make_driver()

        opts = mock_chrome_cls.call_args[1]["options"]
        ua_args = [a for a in opts.arguments if a.startswith("user-agent=")]
        assert len(ua_args) == 1
        assert "Chrome/" in ua_args[0]

    @patch("negotium.sources.driver.webdriver.Chrome")
    def test_disables_automation_flags(self, mock_chrome_cls):
        from negotium.sources.driver import make_driver

        mock_driver = MagicMock()
        mock_chrome_cls.return_value = mock_driver

        make_driver()

        opts = mock_chrome_cls.call_args[1]["options"]
        exp_opts = opts.experimental_options
        assert "excludeSwitches" in exp_opts
        assert "enable-automation" in exp_opts["excludeSwitches"]
        assert exp_opts.get("useAutomationExtension") is False

    @patch("negotium.sources.driver.webdriver.Chrome")
    def test_removes_webdriver_navigator_flag(self, mock_chrome_cls):
        from negotium.sources.driver import make_driver

        mock_driver = MagicMock()
        mock_chrome_cls.return_value = mock_driver

        make_driver()

        mock_driver.execute_cdp_cmd.assert_called_once_with(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )

    @patch("negotium.sources.driver.webdriver.Chrome")
    def test_sets_window_size(self, mock_chrome_cls):
        from negotium.sources.driver import make_driver

        mock_driver = MagicMock()
        mock_chrome_cls.return_value = mock_driver

        make_driver()

        opts = mock_chrome_cls.call_args[1]["options"]
        args = opts.arguments
        assert "--window-size=1920,1080" in args


# ─── Driver lifecycle tests (all sources) ─────────────────────────────────────


class TestDriverLifecycle:
    """Ensure every Selenium-based source creates and quits the driver."""

    @patch("negotium.sources.search_engines.indeed.make_undetected_driver")
    def test_indeed_quits_driver_on_success(self, mock_make):
        from negotium.sources.search_engines.indeed import IndeedSource

        mock_driver = MagicMock()
        mock_driver.page_source = "<html></html>"
        mock_make.return_value = mock_driver

        source = IndeedSource(max_pages=1)
        source.fetch_jobs()

        mock_driver.quit.assert_called_once()

    @patch("negotium.sources.search_engines.indeed.make_undetected_driver")
    def test_indeed_quits_driver_on_exception(self, mock_make):
        from negotium.sources.search_engines.indeed import IndeedSource

        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("crash")
        mock_make.return_value = mock_driver

        source = IndeedSource(max_pages=1)
        source.fetch_jobs()

        mock_driver.quit.assert_called_once()

    @patch("negotium.sources.search_engines.dice.make_driver")
    def test_dice_quits_driver_on_success(self, mock_make):
        from negotium.sources.search_engines.dice import DiceSource

        mock_driver = MagicMock()
        mock_driver.page_source = "<html></html>"
        mock_make.return_value = mock_driver

        source = DiceSource(max_pages=1)
        source.fetch_jobs()

        mock_driver.quit.assert_called_once()

    @patch("negotium.sources.search_engines.dice.make_driver")
    def test_dice_quits_driver_on_exception(self, mock_make):
        from negotium.sources.search_engines.dice import DiceSource

        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("crash")
        mock_make.return_value = mock_driver

        source = DiceSource(max_pages=1)
        source.fetch_jobs()

        mock_driver.quit.assert_called_once()

    @patch("negotium.sources.search_engines.glassdoor.make_driver")
    def test_glassdoor_quits_driver_on_success(self, mock_make):
        from negotium.sources.search_engines.glassdoor import GlassdoorSource

        mock_driver = MagicMock()
        mock_driver.page_source = "<html></html>"
        mock_make.return_value = mock_driver

        source = GlassdoorSource(max_pages=1)
        source.fetch_jobs()

        mock_driver.quit.assert_called_once()

    @patch("negotium.sources.search_engines.glassdoor.make_driver")
    def test_glassdoor_quits_driver_on_exception(self, mock_make):
        from negotium.sources.search_engines.glassdoor import GlassdoorSource

        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("crash")
        mock_make.return_value = mock_driver

        source = GlassdoorSource(max_pages=1)
        source.fetch_jobs()

        mock_driver.quit.assert_called_once()

    @patch("negotium.sources.search_engines.flexjobs.make_driver")
    def test_flexjobs_quits_driver_on_success(self, mock_make):
        from negotium.sources.search_engines.flexjobs import FlexJobsSource

        mock_driver = MagicMock()
        mock_driver.page_source = "<html></html>"
        mock_make.return_value = mock_driver

        source = FlexJobsSource(max_pages=1)
        source.fetch_jobs()

        mock_driver.quit.assert_called_once()

    @patch("negotium.sources.search_engines.flexjobs.make_driver")
    def test_flexjobs_quits_driver_on_exception(self, mock_make):
        from negotium.sources.search_engines.flexjobs import FlexJobsSource

        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("crash")
        mock_make.return_value = mock_driver

        source = FlexJobsSource(max_pages=1)
        source.fetch_jobs()

        mock_driver.quit.assert_called_once()

    @patch("negotium.sources.search_engines.handshake.make_driver")
    def test_handshake_quits_driver_on_success(self, mock_make):
        from negotium.sources.search_engines.handshake import HandshakeSource

        mock_driver = MagicMock()
        mock_driver.page_source = "<html></html>"
        mock_make.return_value = mock_driver

        source = HandshakeSource(max_pages=1)
        source.fetch_jobs()

        mock_driver.quit.assert_called_once()

    @patch("negotium.sources.search_engines.handshake.make_driver")
    def test_handshake_quits_driver_on_exception(self, mock_make):
        from negotium.sources.search_engines.handshake import HandshakeSource

        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("crash")
        mock_make.return_value = mock_driver

        source = HandshakeSource(max_pages=1)
        source.fetch_jobs()

        mock_driver.quit.assert_called_once()

    @patch("negotium.sources.search_engines.ziprecruiter.make_driver")
    def test_ziprecruiter_quits_driver_on_success(self, mock_make):
        from negotium.sources.search_engines.ziprecruiter import ZipRecruiterSource

        mock_driver = MagicMock()
        mock_driver.page_source = "<html></html>"
        mock_make.return_value = mock_driver

        source = ZipRecruiterSource(max_pages=1)
        source.fetch_jobs()

        mock_driver.quit.assert_called_once()

    @patch("negotium.sources.search_engines.ziprecruiter.make_driver")
    def test_ziprecruiter_quits_driver_on_exception(self, mock_make):
        from negotium.sources.search_engines.ziprecruiter import ZipRecruiterSource

        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("crash")
        mock_make.return_value = mock_driver

        source = ZipRecruiterSource(max_pages=1)
        source.fetch_jobs()

        mock_driver.quit.assert_called_once()


# ─── Empty page handling ─────────────────────────────────────────────────────


class TestEmptyPageHandling:
    """Ensure sources return empty lists when no cards are found."""

    @patch("negotium.sources.search_engines.indeed.make_undetected_driver")
    def test_indeed_empty_page(self, mock_make):
        from negotium.sources.search_engines.indeed import IndeedSource

        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body></body></html>"
        mock_make.return_value = mock_driver

        source = IndeedSource(max_pages=1)
        assert source.fetch_jobs() == []

    @patch("negotium.sources.search_engines.dice.make_driver")
    def test_dice_empty_page(self, mock_make):
        from negotium.sources.search_engines.dice import DiceSource

        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body></body></html>"
        mock_make.return_value = mock_driver

        source = DiceSource(max_pages=1)
        assert source.fetch_jobs() == []

    @patch("negotium.sources.search_engines.glassdoor.make_driver")
    def test_glassdoor_empty_page(self, mock_make):
        from negotium.sources.search_engines.glassdoor import GlassdoorSource

        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body></body></html>"
        mock_make.return_value = mock_driver

        source = GlassdoorSource(max_pages=1)
        assert source.fetch_jobs() == []

    @patch("negotium.sources.search_engines.flexjobs.make_driver")
    def test_flexjobs_empty_page(self, mock_make):
        from negotium.sources.search_engines.flexjobs import FlexJobsSource

        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body></body></html>"
        mock_make.return_value = mock_driver

        source = FlexJobsSource(max_pages=1)
        assert source.fetch_jobs() == []

    @patch("negotium.sources.search_engines.handshake.make_driver")
    def test_handshake_empty_page(self, mock_make):
        from negotium.sources.search_engines.handshake import HandshakeSource

        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body></body></html>"
        mock_make.return_value = mock_driver

        source = HandshakeSource(max_pages=1)
        assert source.fetch_jobs() == []

    @patch("negotium.sources.search_engines.ziprecruiter.make_driver")
    def test_ziprecruiter_empty_page(self, mock_make):
        from negotium.sources.search_engines.ziprecruiter import ZipRecruiterSource

        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body></body></html>"
        mock_make.return_value = mock_driver

        source = ZipRecruiterSource(max_pages=1)
        assert source.fetch_jobs() == []
