from __future__ import annotations

from app.schemas.actions import ActionDefinition, ActionId, RiskLevel


class ActionRegistry:
    """The sole list of executable capabilities. IDs are a fixed API contract."""

    def __init__(self) -> None:
        # IDs are enabled for planning and approval; the default adapter does not mutate a system.
        definitions = [
            ActionDefinition(action_id=ActionId.DISABLE_STARTUP_APP, name="Disable startup application", description="Disable one discovered startup entry.", risk_level=RiskLevel.MEDIUM, requires_approval=True, parameter_schema={"type": "object", "properties": {"startup_entry_id": {"type": "string"}}, "required": ["startup_entry_id"], "additionalProperties": False}, executor_name="disable_startup_app", verifier_name="verify_startup_count", enabled=True),
            ActionDefinition(action_id=ActionId.CLEAR_TEMP_FILES, name="Clear approved temporary files", description="Remove files only from approved temporary locations.", risk_level=RiskLevel.MEDIUM, requires_approval=True, parameter_schema={"type": "object", "properties": {}, "additionalProperties": False}, executor_name="clear_temp_files", verifier_name="verify_temp_usage", enabled=True),
            ActionDefinition(action_id=ActionId.REMOVE_OPTIONAL_APP, name="Remove optional application", description="Remove an allowlisted optional application.", risk_level=RiskLevel.MEDIUM, requires_approval=True, parameter_schema={"type": "object", "properties": {"package_id": {"type": "string"}}, "required": ["package_id"], "additionalProperties": False}, executor_name="remove_optional_app", verifier_name="verify_optional_app_absent", enabled=True),
            ActionDefinition(action_id=ActionId.APPLY_PRIVACY_PROFILE, name="Apply privacy profile", description="Apply a named, reviewed privacy profile.", risk_level=RiskLevel.MEDIUM, requires_approval=True, parameter_schema={"type": "object", "properties": {"profile": {"enum": ["balanced"]}}, "required": ["profile"], "additionalProperties": False}, executor_name="apply_privacy_profile", verifier_name="verify_privacy_profile", enabled=True),
            ActionDefinition(action_id=ActionId.RUN_SFC_SCAN, name="Run System File Checker", description="Scans protected Windows system files and attempts to repair corrupted files.", risk_level=RiskLevel.MEDIUM, requires_approval=True, parameter_schema={"type": "object", "properties": {}, "additionalProperties": False}, executor_name="run_sfc_scan", verifier_name="verify_sfc_result", enabled=True),
            ActionDefinition(action_id=ActionId.RUN_DISM_HEALTH_CHECK, name="Run DISM health check", description="Run predefined DISM health check through the controlled executor.", risk_level=RiskLevel.MEDIUM, requires_approval=True, parameter_schema={"type": "object", "properties": {}, "additionalProperties": False}, executor_name="run_dism_health_check", verifier_name="verify_dism_result", enabled=True),
            ActionDefinition(action_id=ActionId.RESTART_WINDOWS_EXPLORER, name="Restart Windows Explorer", description="Safely starts or restarts the Windows Explorer shell process (explorer.exe).", risk_level=RiskLevel.MEDIUM, requires_approval=True, parameter_schema={"type": "object", "properties": {}, "additionalProperties": False}, executor_name="restart_windows_explorer", verifier_name="verify_explorer_process", enabled=True),
        ]
        self._definitions = {definition.action_id: definition for definition in definitions}

    def get(self, action_id: ActionId) -> ActionDefinition:
        return self._definitions[action_id]

    def list(self) -> list[ActionDefinition]:
        return list(self._definitions.values())


registry = ActionRegistry()
