import uuid
from typing import Any

from pydantic import BaseModel, Field


class GuestHeartbeatRequest(BaseModel):
    visitor_id: uuid.UUID
    timezone: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, max_length=16)
    entry_count: int = Field(default=0, ge=0)
    onboarding_completed: bool = False


class GuestHeartbeatResponse(BaseModel):
    ok: bool = True


class GuestImportRequest(BaseModel):
    visitor_id: uuid.UUID
    payload: dict[str, Any]


class GuestImportResponse(BaseModel):
    imported_entries: int
    skipped: bool = False


class GuestExperimentSummaryResponse(BaseModel):
    control_visitors: int
    treatment_visitors: int
    treatment_active_7d: int
    control_converted: int
    treatment_converted: int
    treatment_median_entry_count_on_convert: float | None
    treatment_existing_login_skipped: int
