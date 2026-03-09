"""
Company career-page sources — stubs for future implementation.

To add a new company career page, subclass :class:`CompanyWebsite` and
implement :meth:`fetch_jobs` with the site-specific selectors / API.

Example skeleton::

    @dataclass
    class AppleCareersSource(CompanyWebsite):
        base_url: str = "https://jobs.apple.com/api/role/search"
        keywords: str = "software engineer"

        @property
        def name(self) -> str:
            return "Apple Careers"

        def fetch_jobs(self) -> list[Job]:
            # hit the API, parse JSON, return list[Job]
            ...
"""
