import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Optional


@dataclass
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str
    sender_name: str
    sender_email: str


class SmtpSender:
    def __init__(self, config: SmtpConfig) -> None:
        self.config = config

    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        attachment_path: str,
    ) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{self.config.sender_name} <{self.config.sender_email}>"
        message["To"] = recipient
        message.set_content(body)

        attachment = Path(attachment_path)
        with attachment.open("rb") as handle:
            message.add_attachment(
                handle.read(),
                maintype="application",
                subtype=attachment.suffix.lstrip("."),
                filename=attachment.name,
            )

        with smtplib.SMTP(self.config.host, self.config.port) as server:
            server.starttls()
            server.login(self.config.username, self.config.password)
            server.send_message(message)


def load_smtp_config() -> Optional[SmtpConfig]:
    required = [
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_SENDER_NAME",
        "SMTP_SENDER_EMAIL",
    ]
    if not all(os.getenv(key) for key in required):
        return None
    return SmtpConfig(
        host=os.environ["SMTP_HOST"],
        port=int(os.environ.get("SMTP_PORT", "587")),
        username=os.environ["SMTP_USERNAME"],
        password=os.environ["SMTP_PASSWORD"],
        sender_name=os.environ["SMTP_SENDER_NAME"],
        sender_email=os.environ["SMTP_SENDER_EMAIL"],
    )
