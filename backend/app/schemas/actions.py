from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionId(str, Enum):
    DISABLE_STARTUP_APP = "disable_startup_app"
    CLEAR_TEMP_FILES = "clear_temp_files"
    REMOVE_OPTIONAL_APP = "remove_optional_app"
    APPLY_PRIVACY_PROFILE = "apply_privacy_profile"
    RUN_SFC_SCAN = "run_sfc_scan"
    RUN_DISM_HEALTH_CHECK = "run_dism_health_check"
    RESTART_WINDOWS_EXPLORER = "restart_windows_explorer"

    @classmethod
    def _missing_(cls, value: object) -> ActionId | None:
        if isinstance(value, str):
            val_lower = value.lower()
            for member in cls:
                if member.value == val_lower or member.name == value.upper():
                    return member
        return None


class RecommendedAction(BaseModel):
    """An agent recommendation. It is not an execution request."""

    action_id: ActionId
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


class ActionDefinition(BaseModel):
    action_id: ActionId
    name: str
    description: str
    risk_level: RiskLevel
    requires_approval: bool
    parameter_schema: dict[str, Any] = Field(default_factory=dict)
    executor_name: str
    verifier_name: str
    enabled: bool = False


class ApprovalDecision(BaseModel):
    action_id: ActionId
    approved: bool


class ApprovalRequest(BaseModel):
    decisions: list[ApprovalDecision] = Field(min_length=1)

    @model_validator(mode="after")
    def no_duplicate_actions(self) -> "ApprovalRequest":
        ids = [decision.action_id for decision in self.decisions]
        if len(ids) != len(set(ids)):
            raise ValueError("each action may have only one approval decision")
        return self


class ExecutionResult(BaseModel):
    action_id: ActionId
    status: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
