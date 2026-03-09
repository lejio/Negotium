"""
ATS platform sources — stubs for future implementation.

To add a new ATS portal, subclass :class:`ATSPlatform` and
implement :meth:`fetch_jobs`.

Workday example skeleton::

    @dataclass
    class WorkdaySource(ATSPlatform):
        tenant_url: str = ""      # e.g. "https://company.wd5.myworkdayjobs.com"
        _company_name: str = ""

        @property
        def platform(self) -> str:
            return "workday"

        @property
        def company_name(self) -> str:
            return self._company_name

        @property
        def name(self) -> str:
            return f"Workday ({self.company_name})"

        def fetch_jobs(self) -> list[Job]:
            # Workday exposes a JSON API at:
            #   {tenant_url}/wday/cxs/{tenant}/jobs
            # POST with {"searchText": ..., "limit": 20, "offset": 0}
            ...

Oracle Cloud example skeleton::

    @dataclass
    class OracleCloudSource(ATSPlatform):
        base_url: str = ""  # e.g. "https://company.fa.us2.oraclecloud.com"

        @property
        def platform(self) -> str:
            return "oracle_cloud"

        @property
        def company_name(self) -> str:
            return self._company_name

        @property
        def name(self) -> str:
            return f"Oracle Cloud ({self.company_name})"

        def fetch_jobs(self) -> list[Job]:
            # Oracle Cloud HCM Career Sites expose REST at:
            #   {base_url}/hcmRestApi/resources/latest/recruitingCEJobRequisitions
            ...
"""
