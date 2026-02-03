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

## Usage
Run the full pipeline:
```bash
python src/main.py --dry-run
```

Remove `--dry-run` to send real emails once SMTP is configured.

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
