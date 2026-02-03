import re
from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse

from .email_validator import EmailValidator


@dataclass
class DiscoveredEmail:
    recruiter_name: str
    email: str
    confidence_score: float
    source: str


def _domain_from_url(url: str) -> str:
    return urlparse(url).netloc


def _guess_domain_from_ats(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "greenhouse.io" in host or "lever.co" in host:
        slug = parsed.path.strip("/").split("/", 1)[0]
        if slug:
            return f"{slug}.com"
    return ""


def _name_parts(name: str) -> tuple[str, str]:
    parts = name.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


def discover_emails(
    recruiter_name: str, company_domain: str, validator: EmailValidator
) -> List[DiscoveredEmail]:
    first, last = _name_parts(recruiter_name)
    candidates = []
    if first and last:
        candidates.extend(
            [
                f"{first}.{last}@{company_domain}",
                f"{first}@{company_domain}",
            ]
        )
    candidates.extend([f"hr@{company_domain}", f"careers@{company_domain}"])

    results: List[DiscoveredEmail] = []
    for email in candidates:
        normalized = email.lower()
        if not re.match(r"[^@]+@[^@]+\.[^@]+", normalized):
            continue
        score = validator.validate(normalized)
        results.append(
            DiscoveredEmail(
                recruiter_name=recruiter_name,
                email=normalized,
                confidence_score=score,
                source="pattern_match",
            )
        )
    return results


def discover_from_careers_url(
    recruiter_name: str, careers_url: str, validator: EmailValidator, company_domain: str | None = None
) -> List[DiscoveredEmail]:
    domain = (company_domain or "").strip().lower()
    if not domain:
        guessed = _guess_domain_from_ats(careers_url)
        domain = guessed if guessed else _domain_from_url(careers_url)
    return discover_emails(recruiter_name, domain, validator)
