import argparse
import csv
import datetime as dt
import os
from pathlib import Path
from typing import Dict, List

import yaml
from dotenv import load_dotenv

from collectors.ats_collector import GreenhouseCollector, LeverCollector, write_companies_csv
from enrichment.recruiter_identifier import identify_recruiters
from enrichment.email_discovery import discover_from_careers_url
from enrichment.email_validator import EmailValidator
from ai.email_personalizer import EmailPersonalizer
from compliance.unsubscribe_footer import UnsubscribeFooter
from mailer.rate_limiter import RateLimiter, read_logs
from mailer.smtp_sender import SmtpSender, load_smtp_config


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def write_recruiters_csv(path: str, recruiters: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["company_name", "recruiter_name", "role", "profile_url", "source"])
        for recruiter in recruiters:
            writer.writerow(
                [
                    recruiter.company_name,
                    recruiter.recruiter_name,
                    recruiter.role,
                    recruiter.profile_url,
                    recruiter.source,
                ]
            )


def write_emails_csv(path: str, emails: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["recruiter_name", "email", "confidence_score", "source"])
        for email in emails:
            writer.writerow([email.recruiter_name, email.email, email.confidence_score, email.source])


def append_log(path: str, row: dict) -> None:
    file_exists = Path(path).exists()
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["email", "company", "timestamp", "status"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="HR outreach automation")
    parser.add_argument("--dry-run", action="store_true", help="Do not send emails, only log.")
    args = parser.parse_args()

    load_dotenv()

    base_dir = Path(__file__).resolve().parents[1]
    config_dir = base_dir / "config"
    data_dir = base_dir / "data"

    job_sources = load_yaml(str(config_dir / "job_sources.yaml"))
    email_config = load_yaml(str(config_dir / "email_config.yaml"))

    greenhouse = GreenhouseCollector()
    lever = LeverCollector()

    jobs = []
    for entry in job_sources.get("ats_sources", {}).get("greenhouse", []):
        jobs.extend(greenhouse.fetch_jobs(entry["company_slug"], entry["careers_url"]))
    for entry in job_sources.get("ats_sources", {}).get("lever", []):
        jobs.extend(lever.fetch_jobs(entry["company_slug"], entry["careers_url"]))

    write_companies_csv(str(data_dir / "companies.csv"), jobs)

    recruiters = []
    seen_companies = set()
    for job in jobs:
        if job.company_name in seen_companies:
            continue
        seen_companies.add(job.company_name)
        recruiters.extend(identify_recruiters(job.company_name, job.careers_url))

    write_recruiters_csv(str(data_dir / "recruiters.csv"), recruiters)

    validator = EmailValidator()
    emails = []
    recruiter_company_map: Dict[str, str] = {}
    for recruiter in recruiters:
        recruiter_company_map[recruiter.recruiter_name] = recruiter.company_name
        emails.extend(discover_from_careers_url(recruiter.recruiter_name, recruiter.profile_url, validator))

    write_emails_csv(str(data_dir / "emails.csv"), emails)

    personalizer = EmailPersonalizer(str(config_dir / "prompt_templates"))
    footer_text = email_config.get("compliance", {}).get("unsubscribe_text", "")
    footer = UnsubscribeFooter(text=footer_text)

    smtp_config = load_smtp_config()
    sender = SmtpSender(smtp_config) if smtp_config else None

    rate_limit = RateLimiter(
        daily_limit=int(os.getenv("DAILY_EMAIL_LIMIT", email_config["rate_limit"]["daily_limit"])),
        min_seconds_between_sends=email_config["rate_limit"]["min_seconds_between_sends"],
    )
    logs = read_logs(os.getenv("EMAIL_LOG_PATH", str(data_dir / "sent_logs.csv")))
    already_sent = {row.get("email") for row in logs}

    candidate_profile = os.getenv("CANDIDATE_PROFILE", "relevant experience and skills")
    candidate_name = os.getenv("CANDIDATE_NAME", "Candidate Name")
    candidate_email = os.getenv("CANDIDATE_EMAIL", "candidate@example.com")

    job_lookup = {job.company_name: job for job in jobs}

    for email in emails:
        if email.email in already_sent:
            continue
        if not rate_limit.can_send(logs):
            break

        company = recruiter_company_map.get(email.recruiter_name, "")
        job = job_lookup.get(company)
        context = {
            "company_name": company,
            "job_title": job.job_title if job else "open role",
            "location": job.location if job else "the United States",
            "recruiter_name": email.recruiter_name,
            "recruiter_role": "Recruiter",
            "candidate_profile": candidate_profile,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
        }
        personalized = personalizer.personalize(context)
        body = f"{personalized.body}{footer.render()}"

        status = "skipped"
        try:
            if args.dry_run or not sender:
                status = "dry_run"
            else:
                sender.send_email(
                    recipient=email.email,
                    subject=personalized.subject,
                    body=body,
                    attachment_path=os.getenv("RESUME_PATH", str(base_dir / "resumes" / "candidate_resume.pdf")),
                )
                status = "sent"
        except Exception:
            status = "failed"

        timestamp = dt.datetime.utcnow().isoformat()
        log_path = os.getenv("EMAIL_LOG_PATH", str(data_dir / "sent_logs.csv"))
        append_log(
            log_path,
            {
                "email": email.email,
                "company": company,
                "timestamp": timestamp,
                "status": status,
            },
        )
        logs.append({"email": email.email, "timestamp": timestamp})


if __name__ == "__main__":
    main()
