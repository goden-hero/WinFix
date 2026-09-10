from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas.actions import ActionId, ExecutionResult
from app.schemas.diagnosis import DiagnosisResult
from app.schemas.evidence import Evidence
from app.schemas.verification import VerificationResult


class SessionStatus(str, Enum):
    CREATED = "created"
    DIAGNOSING = "diagnosing"
    DIAGNOSED = "diagnosed"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class WinFixSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_problem: str = Field(min_length=3, max_length=4_000)
    status: SessionStatus = SessionStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evidence: list[Evidence] = Field(default_factory=list)
    diagnosis: DiagnosisResult | None = None
    approvals: dict[ActionId, bool] = Field(default_factory=dict)
    execution_results: list[ExecutionResult] = Field(default_factory=list)
    verification_results: list[VerificationResult] = Field(default_factory=list)


class CreateSessionRequest(BaseModel):
    user_problem: str = Field(min_length=3, max_length=4_000)


class DiagnoseRequest(BaseModel):
    categories: list[str] = Field(default_factory=lambda: ["performance"])
