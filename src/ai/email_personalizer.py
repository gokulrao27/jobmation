from dataclasses import dataclass
from typing import Dict

from jinja2 import Environment, FileSystemLoader


@dataclass
class PersonalizedEmail:
    subject: str
    body: str


class EmailPersonalizer:
    def __init__(self, template_dir: str) -> None:
        self.env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
        self.template = self.env.get_template("outreach_email.txt")

    def personalize(self, context: Dict[str, str]) -> PersonalizedEmail:
        subject = f"Interest in {context.get('job_title', 'open role')} at {context.get('company_name', '')}".strip()
        body = self.template.render(subject=subject, **context)
        return PersonalizedEmail(subject=subject, body=body)
