import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
import mimetypes
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
        if attachment.exists():
            mime_type, _ = mimetypes.guess_type(str(attachment))
            if mime_type:
                maintype, subtype = mime_type.split("/", 1)
            else:
                maintype, subtype = "application", "octet-stream"
            with attachment.open("rb") as handle:
                message.add_attachment(
                    handle.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=attachment.name,
                )
        else:
            # Attachment missing - warn and continue without attachment
            print(f"[warn] Attachment not found at {attachment}; sending without attachment")

        # Use implicit SSL for port 465, otherwise use STARTTLS
        if self.config.port == 465:
            server_ctx = smtplib.SMTP_SSL(self.config.host, self.config.port)
        else:
            server_ctx = smtplib.SMTP(self.config.host, self.config.port)

        with server_ctx as server:
            # For non-SSL connections, attempt STARTTLS
            if self.config.port != 465:
                try:
                    server.starttls()
                except Exception:
                    # If STARTTLS fails, continue and let login raise if necessary
                    print("[warn] STARTTLS failed or not supported by server; continuing without STARTTLS")
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
