from __future__ import annotations

from app.executor.registry import ActionRegistry
from app.executor.winutil_adapter import NativeWindowsAdapter, WinUtilAdapter
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
        return self.adapter.execute(recommendation.action_id, recommendation.parameters)
