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
        verify_url = f"{settings.app_public_url}/v1/auth/verify-email"
        body = (
            "Confirm your Mood Tracker account.\n\n"
            f"POST {verify_url}\n"
            f'Body: {{"token": "{token}"}}\n\n'
            f"Or use this token directly: {token}\n"
        )
        self._send(to=to, subject="Verify your Mood Tracker email", body=body)

    def send_password_reset_email(self, *, to: str, token: str) -> None:
        reset_url = f"{settings.app_public_url}/v1/auth/reset-password"
        body = (
            "Reset your Mood Tracker password.\n\n"
            f"POST {reset_url}\n"
            f'Body: {{"token": "{token}", "new_password": "your-new-password"}}\n\n'
            f"Or use this token directly: {token}\n"
        )
        self._send(to=to, subject="Reset your Mood Tracker password", body=body)

    def _send(self, *, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = settings.email_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)

        self._outbox.append(SentEmail(to=to, subject=subject, body=body))


email_service = EmailService()
