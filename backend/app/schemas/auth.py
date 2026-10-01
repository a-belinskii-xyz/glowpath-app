from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator


class VerificationResendStatus(StrEnum):
    EMAIL_SENT = "email_sent"
    ALREADY_VERIFIED = "already_verified"
    REQUEST_ACCEPTED = "request_accepted"


class PasswordResetRequestStatus(StrEnum):
    EMAIL_SENT = "email_sent"
    REQUEST_ACCEPTED = "request_accepted"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str = Field(min_length=8, max_length=128)
    timezone: str = Field(default="Europe/Minsk", max_length=64)
    visitor_id: str | None = Field(default=None, max_length=36)

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    visitor_id: str | None = Field(default=None, max_length=36)


class TokenRequest(BaseModel):
    token: str = Field(min_length=1)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
    password_confirm: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self


class EmailRequest(BaseModel):
    email: EmailStr


class GoogleIdTokenRequest(BaseModel):
    id_token: str = Field(min_length=1)
    visitor_id: str | None = Field(default=None, max_length=36)


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1, max_length=8192)
    timezone: str = Field(default="Europe/Minsk", max_length=64)


class TelegramBotLoginStartRequest(BaseModel):
    timezone: str = Field(default="Europe/Minsk", max_length=64)


class TelegramBotLoginStartResponse(BaseModel):
    poll_token: str
    deep_link: str
    expires_at: datetime


class TelegramBotLoginPollRequest(BaseModel):
    poll_token: str = Field(min_length=16, max_length=128)


class TelegramBotLoginPollResponse(BaseModel):
    status: Literal["pending", "confirmed", "expired"]
    access_token: str | None = None
    refresh_token: str | None = None
    user_created: bool | None = None


class AttachEmailRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "AttachEmailRequest":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_created: bool | None = None


class MessageResponse(BaseModel):
    message: str


class VerificationResendResponse(BaseModel):
    message: str
    status: VerificationResendStatus


class PasswordResetRequestResponse(BaseModel):
    message: str
    status: PasswordResetRequestStatus
