import re
import smtplib
from dataclasses import dataclass
from typing import Optional


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class EmailValidator:
    smtp_host: Optional[str] = None
    smtp_port: int = 25
    timeout: int = 10

    def validate(self, email: str) -> float:
        if not EMAIL_PATTERN.match(email):
            return 0.0

        if not self.smtp_host:
            return 0.5

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                server.noop()
            return 0.7
        except (smtplib.SMTPException, OSError):
            return 0.4
