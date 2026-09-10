from __future__ import annotations

from app.executor.registry import ActionRegistry
from app.safety.policy import SafetyPolicy
from app.schemas.actions import RecommendedAction


class ActionValidationError(ValueError):
    pass


class ActionValidator:
    """Validates agent recommendations against registry-owned definitions."""

    def __init__(self, registry: ActionRegistry) -> None:
        self.registry = registry

    def validate_recommendation(self, recommendation: RecommendedAction) -> None:
        definition = self.registry.get(recommendation.action_id)
        if not definition.enabled:
            raise ActionValidationError(f"action {recommendation.action_id.value} is not enabled")
        allowed = set(definition.parameter_schema.get("properties", {}))
        unexpected = set(recommendation.parameters) - allowed
        if unexpected:
            raise ActionValidationError(f"unsupported action parameters: {sorted(unexpected)}")

    def validate_execution(self, recommendation: RecommendedAction, approved: bool) -> None:
        self.validate_recommendation(recommendation)
        definition = self.registry.get(recommendation.action_id)
        if not SafetyPolicy.may_execute(definition.risk_level, approved):
            raise ActionValidationError(f"action {recommendation.action_id.value} is blocked by safety policy")
