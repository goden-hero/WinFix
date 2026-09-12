"""Controlled Windows Registry executor for disabling startup applications.

Operates directly using Python's winreg API on HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
No shell commands, subprocesses, PowerShell, CMD, or arbitrary registry scripts are used.
"""

from __future__ import annotations

import platform
from typing import Any

from app.diagnostics.startup import (
    get_startup_apps,
    is_demo_startup_entry,
    parse_startup_entry_id,
)
from app.schemas.actions import ActionId, ExecutionResult


from datetime import datetime, timezone


def disable_startup_app(startup_entry_id: str) -> ExecutionResult:
    """Disable an allowlisted startup entry in HKCU Run by relocating it to RunDisabled."""
    if platform.system() != "Windows":
        return ExecutionResult(
            action_id=ActionId.DISABLE_STARTUP_APP,
            status="failed",
            message="Disabling startup applications is only supported on Windows.",
            details={"startup_entry_id": startup_entry_id},
        )

    try:
        name = parse_startup_entry_id(startup_entry_id)
    except ValueError as err:
        return ExecutionResult(
            action_id=ActionId.DISABLE_STARTUP_APP,
            status="failed",
            message=f"Invalid startup entry identifier: {err}",
            details={"startup_entry_id": startup_entry_id},
        )

    if not is_demo_startup_entry(name):
        return ExecutionResult(
            action_id=ActionId.DISABLE_STARTUP_APP,
            status="failed",
            message=f"Startup entry '{name}' is not in the demo safe allowlist.",
            details={"startup_entry_id": startup_entry_id, "name": name},
        )

    import winreg  # type: ignore[attr-defined]

    run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    disabled_key_path = r"Software\Microsoft\Windows\CurrentVersion\RunDisabled"

    # Capture BEFORE diagnostic snapshot
    diag_before = get_startup_apps()
    total_before = diag_before.get("total_count", 0)
    enabled_before = diag_before.get("enabled_count", 0)

    # Read active entries and find target
    command_to_backup: str | None = None
    unrelated_before: dict[str, str] = {}

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key_path, 0, winreg.KEY_READ) as key:
            index = 0
            while True:
                try:
                    val_name, val_command, _ = winreg.EnumValue(key, index)
                    if val_name == name:
                        command_to_backup = str(val_command)
                    else:
                        unrelated_before[val_name] = str(val_command)
                    index += 1
                except OSError:
                    break
    except OSError as err:
        return ExecutionResult(
            action_id=ActionId.DISABLE_STARTUP_APP,
            status="failed",
            message=f"Failed to access HKCU Run key: {err}",
            details={"startup_entry_id": startup_entry_id},
        )

    if command_to_backup is None:
        return ExecutionResult(
            action_id=ActionId.DISABLE_STARTUP_APP,
            status="failed",
            message=f"Startup entry '{name}' was not found in HKCU Run key.",
            details={"startup_entry_id": startup_entry_id, "name": name},
        )

    # Check for collision in RunDisabled key
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, disabled_key_path, 0, winreg.KEY_READ) as disabled_key:
            existing_cmd, _ = winreg.QueryValueEx(disabled_key, name)
            if str(existing_cmd) != command_to_backup:
                return ExecutionResult(
                    action_id=ActionId.DISABLE_STARTUP_APP,
                    status="failed",
                    message=f"Collision detected: 'RunDisabled\\{name}' already exists with a different command.",
                    details={"startup_entry_id": startup_entry_id, "name": name},
                )
    except OSError:
        pass

    # Perform native winreg relocation to RunDisabled with rollback protection
    try:
        # 1. Ensure RunDisabled key exists and write the backup entry
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, disabled_key_path) as disabled_key:
            winreg.SetValueEx(disabled_key, name, 0, winreg.REG_SZ, command_to_backup)
    except OSError as err:
        return ExecutionResult(
            action_id=ActionId.DISABLE_STARTUP_APP,
            status="failed",
            message=f"Failed to create backup entry in RunDisabled for '{name}': {err}",
            details={"startup_entry_id": startup_entry_id, "name": name},
        )

    try:
        # 2. Delete entry from HKCU Run
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key_path, 0, winreg.KEY_SET_VALUE) as run_key:
            winreg.DeleteValue(run_key, name)
    except OSError as err:
        # Rollback: attempt to delete the newly created backup value in RunDisabled so system remains consistent
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, disabled_key_path, 0, winreg.KEY_SET_VALUE) as disabled_key:
                winreg.DeleteValue(disabled_key, name)
        except OSError:
            pass

        return ExecutionResult(
            action_id=ActionId.DISABLE_STARTUP_APP,
            status="failed",
            message=f"Failed to remove original HKCU Run entry '{name}'. Rolled back RunDisabled backup. Error: {err}",
            details={"startup_entry_id": startup_entry_id, "name": name},
        )

    # Capture AFTER diagnostic snapshot
    diag_after = get_startup_apps()
    total_after = diag_after.get("total_count", 0)
    enabled_after = diag_after.get("enabled_count", 0)

    return ExecutionResult(
        action_id=ActionId.DISABLE_STARTUP_APP,
        status="success",
        message=f"Disabled startup entry '{name}' in HKCU Run.",
        details={
            "startup_entry_id": startup_entry_id,
            "name": name,
            "command": command_to_backup,
            "original_source": "HKCU_RUN",
            "original_enabled": True,
            "disabled_at": datetime.now(timezone.utc).isoformat(),
            "state_before": "ENABLED",
            "state_after": "DISABLED",
            "total_entries_before": total_before,
            "enabled_entries_before": enabled_before,
            "total_entries_after": total_after,
            "enabled_entries_after": enabled_after,
            "unrelated_entries_before": unrelated_before,
        },
    )
