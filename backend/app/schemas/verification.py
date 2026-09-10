from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.actions import ActionId


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    NOT_VERIFIED = "not_verified"
    SKIPPED = "skipped"
    FAILED = "failed"


class VerificationMetric(BaseModel):
    name: str
    before: Any = None
    after: Any = None
    unit: str | None = None
    improved: bool | None = None


class VerificationResult(BaseModel):
    action_id: ActionId
    status: VerificationStatus
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    metrics: list[VerificationMetric] = Field(default_factory=list)
    summary: str
