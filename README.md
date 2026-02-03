# HR Outreach Automation

A production-ready Python 3 pipeline for sourcing companies hiring in the USA, identifying recruiter contacts from public company pages, discovering compliant email patterns, generating personalized outreach, and sending one email per recipient with a resume attached.

## Features
- Collects job listings from public ATS APIs (Greenhouse, Lever).
- Identifies recruiter contacts from public careers/people pages (no private scraping).
- Discovers likely email patterns and validates syntax.
- Personalizes outreach emails with template-based or optional OpenAI generation.
- Sends emails via SMTP with daily rate limits and unsubscribe footer.
- Logs email sends and avoids duplicates.

## Repository Layout
```
hr-outreach-automation/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── config/
│   ├── job_sources.yaml
│   ├── email_config.yaml
│   └── prompt_templates/
│       └── outreach_email.txt
├── data/
│   ├── companies.csv
│   ├── recruiters.csv
│   ├── emails.csv
│   └── sent_logs.csv
├── resumes/
│   └── candidate_resume.pdf
├── src/
│   ├── collectors/
│   │   ├── ats_collector.py
│   │   └── job_board_collector.py
│   ├── enrichment/
│   │   ├── recruiter_identifier.py
│   │   ├── email_discovery.py
│   │   └── email_validator.py
│   ├── ai/
│   │   └── email_personalizer.py
│   ├── mailer/
│   │   ├── smtp_sender.py
│   │   └── rate_limiter.py
│   ├── compliance/
│   │   └── unsubscribe_footer.py
│   └── main.py
```

## Setup
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
3. Update `.env` with SMTP settings, candidate profile info, and resume path.
4. Update `config/job_sources.yaml` with real ATS company slugs and careers URLs.

## Readiness Checklist (Before Applying)
- ✅ `.env` is populated with working SMTP credentials and sender identity.
- ✅ `RESUME_PATH` points to the resume you want attached (default: `resumes/Narayan Rao Full Stack Developer.docx`).
- ✅ `config/job_sources.yaml` includes real company sources to target (public ATS sources only).
- ✅ `config/prompt_templates/outreach_email.txt` reflects your current resume highlights.
- ✅ Run a dry run first to confirm outputs look correct (`--dry-run`).

## Job Source Coverage (Public Data Only)
This pipeline only uses **public ATS APIs** and **public company pages** to stay compliant. It does **not** scrape private data or paywalled job boards like LinkedIn, Indeed, Monster, or CareerBuilder.

To expand coverage:
- Add more ATS companies under `ats_sources` in `config/job_sources.yaml`.
- Add manual entries from public job boards to `job_boards` and run the pipeline.
- Prefer vendors that publish public APIs or RSS feeds.

## SMTP Configuration & Ports
This project uses **STARTTLS** via `smtplib.SMTP(...).starttls()` in `src/mailer/smtp_sender.py`.

Common SMTP ports:
- **587 (STARTTLS)** → recommended and supported by this project.
- **25 (STARTTLS)** → often blocked by consumer ISPs but can work in corporate networks.
- **465 (SSL/TLS)** → *not supported* by default because the code uses STARTTLS, not implicit TLS.

If your provider requires port **465**, update `smtp_sender.py` to use `smtplib.SMTP_SSL` instead.

## Usage
Run the full pipeline:
```bash
python src/main.py --dry-run
```

Remove `--dry-run` to send real emails once SMTP is configured.

The pipeline will skip any email already recorded in `data/sent_logs.csv` to avoid duplicates. You can control daily volume using `DAILY_EMAIL_LIMIT` in `.env` (default 40).

## Compliance & Safety
- Uses only public ATS APIs and company websites.
- Avoids scraping private data (no LinkedIn scraping).
- Sends one email per recipient with rate limiting.
- Provides an unsubscribe footer in every message.

## Output Data
- `data/companies.csv`: companies and roles gathered from ATS.
- `data/recruiters.csv`: recruiter contacts found on public pages.
- `data/emails.csv`: discovered emails with confidence scores.
- `data/sent_logs.csv`: email send log with status.
