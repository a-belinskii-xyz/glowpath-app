import smtplib
from collections.abc import Mapping
from dataclasses import dataclass
from email.message import EmailMessage

import httpx

from app.config import settings

RESEND_API_URL = "https://api.resend.com/emails"
_SEND_TIMEOUT_SECONDS = 15.0


class EmailSendError(OSError):
    """Raised when the mail provider rejects or cannot accept a message."""


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
            "Confirm your GlowPath account.\n\n"
            f"Click the link below to verify your email:\n\n"
            f"{verify_url}\n"
        )
        self.send(to=to, subject="Verify your GlowPath email", body=body)

    def send_password_reset_email(self, *, to: str, token: str) -> None:
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        body = (
            "Reset your GlowPath password.\n\n"
            f"Click the link below to choose a new password:\n\n"
            f"{reset_url}\n"
        )
        self.send(to=to, subject="Reset your GlowPath password", body=body)

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html_body: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        if settings.resend_api_key.strip():
            self._send_via_resend(
                to=to, subject=subject, body=body, html_body=html_body, headers=headers
            )
        else:
            self._send_via_smtp(
                to=to, subject=subject, body=body, html_body=html_body, headers=headers
            )
        self._outbox.append(SentEmail(to=to, subject=subject, body=body))

    def _send_via_resend(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html_body: str | None,
        headers: Mapping[str, str] | None,
    ) -> None:
        # HTTPS instead of SMTP: Render free web services block outbound SMTP ports.
        payload: dict[str, object] = {
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "text": body,
        }
        if html_body is not None:
            payload["html"] = html_body
        if headers:
            payload["headers"] = dict(headers)
        try:
            response = httpx.post(
                RESEND_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {settings.resend_api_key.strip()}"},
                timeout=_SEND_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise EmailSendError(f"Resend request failed: {exc}") from exc
        if response.status_code >= 400:
            raise EmailSendError(f"Resend rejected email: {response.status_code} {response.text}")

    def _send_via_smtp(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html_body: str | None,
        headers: Mapping[str, str] | None,
    ) -> None:
        message = EmailMessage()
        message["From"] = settings.email_from
        message["To"] = to
        message["Subject"] = subject
        for name, value in (headers or {}).items():
            message[name] = value
        message.set_content(body)
        if html_body is not None:
            message.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(
            settings.smtp_host, settings.smtp_port, timeout=_SEND_TIMEOUT_SECONDS
        ) as smtp:
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)


email_service = EmailService()
