r"""Windows-native startup diagnostic module.

Inspects HKCU\Software\Microsoft\Windows\CurrentVersion\Run (active)
and HKCU\Software\Microsoft\Windows\CurrentVersion\RunDisabled (disabled).
No arbitrary registry access or shell execution is performed.
"""

from __future__ import annotations

import platform
from typing import Any, TypedDict

# Controlled allowlist for hackathon demonstration safe startup entries
DEMO_STARTUP_ENTRIES = {"WinFixDemoUpdater", "WinFixDemoAnalytics", "WinFixDemoHelper"}


def is_demo_startup_entry(name: str) -> bool:
    """Return True if entry is an allowlisted demo startup app."""
    return name in DEMO_STARTUP_ENTRIES or name.startswith("WinFixDemo")


def make_startup_entry_id(name: str) -> str:
    """Format stable identifier for an HKCU Run startup entry."""
    return f"hkcu_run:{name}"


def parse_startup_entry_id(entry_id: str) -> str:
    """Extract entry name from stable startup_entry_id or raise ValueError."""
    if not entry_id or not isinstance(entry_id, str):
        raise ValueError("startup_entry_id must be a non-empty string")
    prefix = "hkcu_run:"
    if not entry_id.startswith(prefix):
        raise ValueError(f"startup_entry_id must start with '{prefix}'")
    name = entry_id[len(prefix):].strip()
    if not name:
        raise ValueError("startup_entry_id name component cannot be empty")
    return name


class StartupDiagnosticResult(TypedDict):
    supported: bool
    platform: str
    source: str
    entries: list[dict[str, Any]]
    total_count: int
    enabled_count: int
    disabled_count: int
    message: str | None


def get_startup_apps() -> StartupDiagnosticResult:
    """Inspect HKCU Run keys and return structured startup application metadata."""
    current_os = platform.system()
    if current_os != "Windows":
        return {
            "supported": False,
            "platform": current_os,
            "source": "HKCU_RUN",
            "entries": [],
            "total_count": 0,
            "enabled_count": 0,
            "disabled_count": 0,
            "message": f"Startup diagnostics require Windows Registry (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run). Current OS '{current_os}' is not supported.",
        }

    try:
        import winreg  # type: ignore[attr-defined]

        entries: list[dict[str, Any]] = []
        enabled_count = 0
        disabled_count = 0

        # Read active entries from HKCU Run
        run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0, winreg.KEY_READ) as key:
                index = 0
                while True:
                    try:
                        name, command, _ = winreg.EnumValue(key, index)
                        entries.append({
                            "id": make_startup_entry_id(name),
                            "name": name,
                            "source": "HKCU_RUN",
                            "enabled": True,
                            "command": str(command),
                            "is_demo": is_demo_startup_entry(name),
                        })
                        enabled_count += 1
                        index += 1
                    except OSError:
                        break
        except OSError:
            pass

        # Read disabled entries from HKCU RunDisabled
        disabled_path = r"Software\Microsoft\Windows\CurrentVersion\RunDisabled"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, disabled_path, 0, winreg.KEY_READ) as key:
                index = 0
                while True:
                    try:
                        name, command, _ = winreg.EnumValue(key, index)
                        entries.append({
                            "id": make_startup_entry_id(name),
                            "name": name,
                            "source": "HKCU_RUN",
                            "enabled": False,
                            "command": str(command),
                            "is_demo": is_demo_startup_entry(name),
                        })
                        disabled_count += 1
                        index += 1
                    except OSError:
                        break
        except OSError:
            pass

        return {
            "supported": True,
            "platform": "Windows",
            "source": "HKCU_RUN",
            "entries": entries,
            "total_count": len(entries),
            "enabled_count": enabled_count,
            "disabled_count": disabled_count,
            "message": None,
        }
    except Exception as exc:
        return {
            "supported": False,
            "platform": "Windows",
            "source": "HKCU_RUN",
            "entries": [],
            "total_count": 0,
            "enabled_count": 0,
            "disabled_count": 0,
            "message": f"Failed to read Registry HKCU Run entries: {exc}",
        }
