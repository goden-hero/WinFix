from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.actions import RecommendedAction


class ProbableCause(BaseModel):
    title: str
    explanation: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class Finding(BaseModel):
    title: str
    description: str
    evidence_ids: list[str] = Field(default_factory=list)


class DiagnosisResult(BaseModel):
    """Structured agent output; facts remain in Evidence, not in this model."""

    summary: str
    probable_causes: list[ProbableCause] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    overall_confidence: float = Field(ge=0, le=1)
    generated_by: str = "deterministic_fallback"
