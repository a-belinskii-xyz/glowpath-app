import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AccountDeleteRequest(BaseModel):
    # Explicit flag so a stray DELETE without a body never wipes an account.
    confirm: bool = False


class AccountExportTelegramResponse(BaseModel):
    parts: int


class RestoreSummary(BaseModel):
    entries_total: int = 0
    entries_new: int = 0
    entries_existing: int = 0
    first_recorded_at: datetime | None = None
    last_recorded_at: datetime | None = None
    tag_groups_new: int = 0
    tags_new: int = 0
    goals_new: int = 0
    note_templates_new: int = 0
    attachments_total: int = 0
    attachments_ready: int = 0
    attachments_lost: int = 0
    parts_total: int = 1
    missing_parts: list[int] = Field(default_factory=list)


class RestoreWarning(BaseModel):
    # ambiguous_tag | unknown_tag | unknown_goal | invalid_attachment
    code: str
    slug: str | None = None
    file: str | None = None


class DiaryRestorePublic(BaseModel):
    id: uuid.UUID
    status: str
    format_version: int
    exported_at: datetime | None
    created_at: datetime
    applied_at: datetime | None
    summary: RestoreSummary
    warnings: list[RestoreWarning]
