from pydantic import BaseModel, Field


class VisitorFingerprintSignals(BaseModel):
    timezone: str = Field(max_length=64)
    screen_width: int = Field(ge=0, le=10000)
    screen_height: int = Field(ge=0, le=10000)
    screen_dpr: float = Field(ge=0.5, le=10)
    platform: str = Field(max_length=128)
    max_touch_points: int = Field(ge=0, le=32)


class FeatureBootstrapRequest(BaseModel):
    fingerprint: VisitorFingerprintSignals | None = None


class FeatureBootstrapResponse(BaseModel):
    visitor_id: str
    guest_local_diary: bool
    cohort: str
    features: dict[str, bool] = Field(default_factory=dict)
