import json
import os
from dataclasses import dataclass
from typing import Dict

import requests
from jinja2 import Environment, FileSystemLoader


@dataclass
class PersonalizedEmail:
    subject: str
    body: str


class EmailPersonalizer:
    def __init__(self, template_dir: str) -> None:
        self.env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
        self.template = self.env.get_template("outreach_email.txt")
        self.api_key = os.getenv("OPENAI_API_KEY")

    def personalize(self, context: Dict[str, str]) -> PersonalizedEmail:
        if self.api_key:
            ai_subject, ai_body = self._generate_with_openai(context)
            return PersonalizedEmail(subject=ai_subject, body=ai_body)

        subject = f"Interest in {context.get('job_title', 'open role')} at {context.get('company_name', '')}".strip()
        body = self.template.render(subject=subject, **context)
        return PersonalizedEmail(subject=subject, body=body)

    def _generate_with_openai(self, context: Dict[str, str]) -> tuple[str, str]:
        prompt = (
            "You are a helpful assistant writing a professional outreach email to a recruiter. "
            "Keep the email concise, respectful, and tailored to the job and company. "
            "Return JSON with keys 'subject' and 'body'.\n\n"
            f"Company: {context.get('company_name')}\n"
            f"Role: {context.get('job_title')}\n"
            f"Recruiter Role: {context.get('recruiter_role')}\n"
            f"Candidate Profile: {context.get('candidate_profile')}\n"
        )
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        try:
            payload = json.loads(content)
            return payload.get("subject", ""), payload.get("body", "")
        except (json.JSONDecodeError, AttributeError):
            subject = f"Interest in {context.get('job_title', 'open role')} at {context.get('company_name', '')}".strip()
            body = self.template.render(subject=subject, **context)
            return subject, body
