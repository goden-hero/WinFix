from __future__ import annotations

from typing import Protocol

from app.executor.temp_cleaner import clear_temp_files
from app.schemas.actions import ActionId, ExecutionResult


class WinUtilAdapter(Protocol):
    """Optional integration point. It receives validated action IDs, never LLM text."""

    def execute(self, action_id: ActionId, parameters: dict[str, object]) -> ExecutionResult: ...


class UnavailableWinUtilAdapter:
    def execute(self, action_id: ActionId, parameters: dict[str, object]) -> ExecutionResult:
        return ExecutionResult(
            action_id=action_id,
            status="not_implemented",
            message="WinUtil integration is not configured for this WinFix installation.",
        )


class NativeWindowsAdapter:
    """Controlled native executor. Dispatches validated ActionIds to bounded backend functions."""

    def __init__(self) -> None:
        self._fallback = UnavailableWinUtilAdapter()

    def execute(self, action_id: ActionId, parameters: dict[str, object]) -> ExecutionResult:
        if action_id == ActionId.CLEAR_TEMP_FILES:
            # Ignore any parameters provided; target root is strictly owned by backend
            return clear_temp_files()
        return self._fallback.execute(action_id, parameters)
