from __future__ import annotations

from app.executor.registry import ActionRegistry
from app.executor.winutil_adapter import NativeWindowsAdapter, WinUtilAdapter
from app.safety.privilege import is_windows_admin
from app.safety.validator import ActionValidator
from app.schemas.actions import ExecutionResult, RecommendedAction


class ControlledExecutor:
    """Execution gateway; it has no command-string API by design."""

    def __init__(self, registry: ActionRegistry, adapter: WinUtilAdapter | None = None) -> None:
        self.registry = registry
        self.validator = ActionValidator(registry)
        self.adapter = adapter or NativeWindowsAdapter()

    def execute(self, recommendation: RecommendedAction, approved: bool) -> ExecutionResult:
        self.validator.validate_execution(recommendation, approved)
        definition = self.registry.get(recommendation.action_id)

        if not definition.implemented:
            return ExecutionResult(
                action_id=recommendation.action_id,
                status="not_implemented",
                message=f"Action '{definition.name}' is intentionally not implemented in the current version.",
                details={"implemented": False},
            )

        if definition.requires_admin and not is_windows_admin():
            return ExecutionResult(
                action_id=recommendation.action_id,
                status="requires_elevation",
                message=f"Action '{definition.name}' requires Administrator privileges.",
                details={"requires_admin": True},
            )

        return self.adapter.execute(recommendation.action_id, recommendation.parameters)
