from __future__ import annotations

from app.diagnostics.startup import is_demo_startup_entry, parse_startup_entry_id
from app.executor.registry import ActionRegistry
from app.safety.policy import SafetyPolicy
from app.schemas.actions import ActionId, RecommendedAction


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

        if recommendation.action_id == ActionId.DISABLE_STARTUP_APP:
            startup_entry_id = recommendation.parameters.get("startup_entry_id")
            if not startup_entry_id or not isinstance(startup_entry_id, str):
                raise ActionValidationError("startup_entry_id is required for DISABLE_STARTUP_APP")
            try:
                name = parse_startup_entry_id(startup_entry_id)
            except ValueError as err:
                raise ActionValidationError(f"invalid startup_entry_id: {err}") from err

            if not is_demo_startup_entry(name):
                raise ActionValidationError(f"startup entry '{name}' is not in the demo safe allowlist")

    def validate_execution(self, recommendation: RecommendedAction, approved: bool) -> None:
        self.validate_recommendation(recommendation)
        definition = self.registry.get(recommendation.action_id)
        if not SafetyPolicy.may_execute(definition.risk_level, approved):
            raise ActionValidationError(f"action {recommendation.action_id.value} is blocked by safety policy")

