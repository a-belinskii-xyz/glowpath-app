import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.config import settings


@dataclass(frozen=True, slots=True)
class SentEmail:
    to: str
    subject: str
    body: str


class EmailService:
    def __init__(self) -> None:
        self._outbox: list[SentEmail] = []

    @property
    def outbox(self) -> list[SentEmail]:
        return list(self._outbox)

    def clear_outbox(self) -> None:
        self._outbox.clear()

    def send_verification_email(self, *, to: str, token: str) -> None:
        verify_url = f"{settings.frontend_url}/verify-email?token={token}"
        body = (
            "Confirm your Mood Tracker account.\n\n"
            f"Click the link below to verify your email:\n\n"
            f"{verify_url}\n"
        )
        self.send(to=to, subject="Verify your Mood Tracker email", body=body)

    def send_password_reset_email(self, *, to: str, token: str) -> None:
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        body = (
            "Reset your Mood Tracker password.\n\n"
            f"Click the link below to choose a new password:\n\n"
            f"{reset_url}\n"
        )
        self.send(to=to, subject="Reset your Mood Tracker password", body=body)

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> None:
        message = EmailMessage()
        message["From"] = settings.email_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        if html_body is not None:
            message.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)

        self._outbox.append(SentEmail(to=to, subject=subject, body=body))


email_service = EmailService()
