import re
from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse

import requests


RECRUITER_KEYWORDS = (
    "recruiter",
    "talent acquisition",
    "people operations",
    "hr",
    "human resources",
)


@dataclass
class RecruiterContact:
    company_name: str
    recruiter_name: str
    role: str
    profile_url: str
    source: str


def _extract_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc


def identify_recruiters(company_name: str, careers_url: str) -> List[RecruiterContact]:
    """
    Identify recruiter contacts by scanning public careers or people pages.
    This method only accesses publicly available company pages.
    """
    recruiters: List[RecruiterContact] = []
    try:
        response = requests.get(careers_url, timeout=20)
        response.raise_for_status()
        text = response.text
    except requests.RequestException:
        return [
            RecruiterContact(
                company_name=company_name,
                recruiter_name="Hiring Team",
                role="Recruiting",
                profile_url=careers_url,
                source="careers_page",
            )
        ]

    for match in re.finditer(
        r"([A-Z][a-z]+\s+[A-Z][a-z]+)[^\n]{0,60}(Recruiter|Talent Acquisition|HR|Human Resources)",
        text,
        re.IGNORECASE,
    ):
        name = match.group(1).strip()
        role = match.group(2).strip()
        recruiters.append(
            RecruiterContact(
                company_name=company_name,
                recruiter_name=name,
                role=role,
                profile_url=careers_url,
                source=_extract_domain(careers_url),
            )
        )

    if not recruiters:
        recruiters.append(
            RecruiterContact(
                company_name=company_name,
                recruiter_name="Hiring Team",
                role="Recruiting",
                profile_url=careers_url,
                source=_extract_domain(careers_url),
            )
        )

    return recruiters
