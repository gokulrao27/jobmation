import csv
import datetime as dt
from dataclasses import dataclass
from typing import Iterable, List, Dict

import requests


@dataclass
class CompanyJob:
    company_name: str
    job_title: str
    location: str
    careers_url: str
    company_domain: str | None = None


class GreenhouseCollector:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    def fetch_jobs(self, company_slug: str, careers_url: str) -> List[CompanyJob]:
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
        try:
            response = self.session.get(api_url, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"[warn] Greenhouse fetch failed for {company_slug}: {exc}")
            return []
        jobs: List[CompanyJob] = []
        for job in payload.get("jobs", []):
            location = job.get("location", {}).get("name", "")
            jobs.append(
                CompanyJob(
                    company_name=job.get("company_name", company_slug),
                    job_title=job.get("title", ""),
                    location=location,
                    careers_url=careers_url,
                )
            )
        return jobs


class LeverCollector:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    def fetch_jobs(self, company_slug: str, careers_url: str) -> List[CompanyJob]:
        api_url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
        try:
            response = self.session.get(api_url, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"[warn] Lever fetch failed for {company_slug}: {exc}")
            return []
        jobs: List[CompanyJob] = []
        for job in payload:
            location = job.get("categories", {}).get("location", "")
            jobs.append(
                CompanyJob(
                    company_name=job.get("company", company_slug),
                    job_title=job.get("text", ""),
                    location=location,
                    careers_url=careers_url,
                )
            )
        return jobs


def write_companies_csv(path: str, jobs: Iterable[CompanyJob]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["company_name", "job_title", "location", "careers_url", "company_domain"])
        for job in jobs:
            writer.writerow(
                [job.company_name, job.job_title, job.location, job.careers_url, job.company_domain or ""]
            )


def log_collection_summary(jobs: Iterable[CompanyJob]) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for job in jobs:
        summary[job.company_name] = summary.get(job.company_name, 0) + 1
    summary["collected_at"] = int(dt.datetime.utcnow().timestamp())
    return summary
