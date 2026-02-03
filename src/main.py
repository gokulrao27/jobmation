import argparse
import csv
import datetime as dt
import os
from pathlib import Path
import shutil
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


def ensure_env_file(base_dir: Path) -> None:
    env_path = base_dir / ".env"
    example_path = base_dir / ".env.example"
    if env_path.exists() or not example_path.exists():
        return
    shutil.copy(example_path, env_path)
    print(f"[info] Created {env_path} from .env.example")


def main() -> None:
    parser = argparse.ArgumentParser(description="HR outreach automation")
    parser.add_argument("--dry-run", action="store_true", help="Do not send emails, only log.")
    parser.add_argument("--no-network", action="store_true", help="Skip external network calls (collectors + SMTP) for local simulation.")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    ensure_env_file(base_dir)
    load_dotenv()
    config_dir = base_dir / "config"
    data_dir = base_dir / "data"
    data_dir.mkdir(exist_ok=True)

    job_sources = load_yaml(str(config_dir / "job_sources.yaml"))
    if args.no_network:
        print("[info] Running in no-network mode: skipping collectors and SMTP")
        # Empty ATS sources to avoid any HTTP calls
        job_sources = {"ats_sources": {"greenhouse": [], "lever": []}}
    email_config = load_yaml(str(config_dir / "email_config.yaml"))

    greenhouse = GreenhouseCollector()
    lever = LeverCollector()

    jobs = []
    for entry in job_sources.get("ats_sources", {}).get("greenhouse", []):
        company_domain = entry.get("company_domain")
        fetched = greenhouse.fetch_jobs(entry["company_slug"], entry["careers_url"])
        for job in fetched:
            job.company_domain = company_domain
        jobs.extend(fetched)
    for entry in job_sources.get("ats_sources", {}).get("lever", []):
        company_domain = entry.get("company_domain")
        fetched = lever.fetch_jobs(entry["company_slug"], entry["careers_url"])
        for job in fetched:
            job.company_domain = company_domain
        jobs.extend(fetched)

    write_companies_csv(str(data_dir / "companies.csv"), jobs)
    print(f"[info] Collected {len(jobs)} jobs.")

    recruiters = []
    seen_companies = set()
    for job in jobs:
        if job.company_name in seen_companies:
            continue
        seen_companies.add(job.company_name)
        recruiters.extend(identify_recruiters(job.company_name, job.careers_url))

    write_recruiters_csv(str(data_dir / "recruiters.csv"), recruiters)
    print(f"[info] Identified {len(recruiters)} recruiter contacts.")

    validator = EmailValidator()
    emails = []
    recruiter_company_map: Dict[str, str] = {}
    company_domain_map: Dict[str, str] = {}
    for job in jobs:
        if job.company_domain:
            company_domain_map[job.company_name] = job.company_domain
    for recruiter in recruiters:
        recruiter_company_map[recruiter.recruiter_name] = recruiter.company_name
        company_domain = company_domain_map.get(recruiter.company_name)
        emails.extend(
            discover_from_careers_url(
                recruiter.recruiter_name,
                recruiter.profile_url,
                validator,
                company_domain=company_domain,
            )
        )

    deduped_emails = {}
    for email in emails:
        if email.email not in deduped_emails:
            deduped_emails[email.email] = email

    emails = list(deduped_emails.values())
    write_emails_csv(str(data_dir / "emails.csv"), emails)
    print(f"[info] Discovered {len(emails)} unique emails.")

    personalizer = EmailPersonalizer(str(config_dir / "prompt_templates"))
    footer_text = email_config.get("compliance", {}).get("unsubscribe_text", "")
    footer = UnsubscribeFooter(text=footer_text)

    smtp_config = load_smtp_config()
    # If running no-network, ensure we don't create an SMTP sender
    if args.no_network:
        sender = None
    else:
        sender = SmtpSender(smtp_config) if smtp_config else None
    if not sender:
        print("[info] SMTP sender not configured; running in dry-run mode.")

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

    if not emails:
        print("[warn] No emails discovered; nothing to send.")

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
