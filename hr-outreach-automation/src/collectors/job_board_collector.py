from dataclasses import dataclass
from typing import List


@dataclass
class JobBoardListing:
    company_name: str
    job_title: str
    location: str
    careers_url: str
    source: str


class ManualJobBoardCollector:
    """
    Use this collector when the job board does not expose a public API.
    Populate listings manually based on publicly available job listings.
    """

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    def collect(self, listings: List[JobBoardListing]) -> List[JobBoardListing]:
        return listings
