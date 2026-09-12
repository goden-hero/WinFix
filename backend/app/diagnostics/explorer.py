"""Read-only Windows Explorer (explorer.exe) diagnostic module.

Inspects explorer.exe process availability, count, and PIDs via a dependency-injected
process provider or psutil, and constructs structured Evidence.
"""

from __future__ import annotations

import platform
from typing import Any, Callable, List, Optional

import psutil

from app.schemas.evidence import Evidence, EvidenceCategory, Severity

KIND_EXPLORER_DIAGNOSIS = "EXPLORER_DIAGNOSIS"
TARGET_PROCESS_NAME = "explorer.exe"


def _default_psutil_provider() -> List[dict[str, Any]]:
    """Default psutil process collector strictly listing explorer.exe processes."""
    records: List[dict[str, Any]] = []
    try:
        for proc in psutil.process_iter(["pid", "name", "status"]):
            try:
                name = proc.info.get("name") or ""
                if name.lower() == TARGET_PROCESS_NAME:
                    status = str(proc.info.get("status") or "running")
                    records.append(
                        {
                            "pid": proc.info.get("pid"),
                            "name": TARGET_PROCESS_NAME,
                            "status": status,
                        }
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass
    return records


def diagnose_explorer(
    proc_provider: Optional[Callable[[], List[dict[str, Any]]]] = None,
) -> Evidence:
    """Collect read-only diagnostic evidence for explorer.exe.
    
    Supports dependency injection via `proc_provider` for safe unit testing without
    a Windows host or running Explorer instance.
    """
    is_windows = platform.system() == "Windows"
    limitations: List[str] = []
    warnings: List[str] = []

    if not is_windows:
        limitations.append("Explorer diagnostics are only available on Windows operating systems.")
        if proc_provider is None:
            return Evidence(
                category=EvidenceCategory.EXPLORER,
                severity=Severity.INFO,
                title="Windows Explorer diagnostic unavailable",
                description="Explorer diagnostics are unsupported on non-Windows platforms.",
                source="diagnose_explorer",
                data={
                    "kind": KIND_EXPLORER_DIAGNOSIS,
                    "process_name": TARGET_PROCESS_NAME,
                    "running": False,
                    "process_count": 0,
                    "process_ids": [],
                    "taskbar_impact": "unknown",
                    "desktop_impact": "unknown",
                    "status": "unsupported",
                    "warnings": [],
                    "limitations": limitations,
                },
            )
        proc_provider = _default_psutil_provider

    try:
        raw_data = proc_provider()
    except Exception as exc:
        limitations.append(f"Failed to query process provider: {exc}")
        return Evidence(
            category=EvidenceCategory.EXPLORER,
            severity=Severity.INFO,
            title="Windows Explorer query limitation",
            description="Process inspection failed or reported invalid data.",
            source="diagnose_explorer",
            data={
                "kind": KIND_EXPLORER_DIAGNOSIS,
                "process_name": TARGET_PROCESS_NAME,
                "running": False,
                "process_count": 0,
                "process_ids": [],
                "taskbar_impact": "unknown",
                "desktop_impact": "unknown",
                "status": "unavailable",
                "warnings": [],
                "limitations": limitations,
            },
        )

    if not isinstance(raw_data, list):
        limitations.append("Process provider returned non-list data structure.")
        return Evidence(
            category=EvidenceCategory.EXPLORER,
            severity=Severity.INFO,
            title="Windows Explorer malformed data",
            description="Process provider returned malformed diagnostic data.",
            source="diagnose_explorer",
            data={
                "kind": KIND_EXPLORER_DIAGNOSIS,
                "process_name": TARGET_PROCESS_NAME,
                "running": False,
                "process_count": 0,
                "process_ids": [],
                "taskbar_impact": "unknown",
                "desktop_impact": "unknown",
                "status": "unavailable",
                "warnings": [],
                "limitations": limitations,
            },
        )

    matching_pids: List[int] = []
    for item in raw_data:
        if not isinstance(item, dict):
            continue
        p_name = str(item.get("name") or "").strip().lower()
        if p_name == TARGET_PROCESS_NAME:
            raw_pid = item.get("pid")
            if raw_pid is not None:
                try:
                    matching_pids.append(int(raw_pid))
                except (ValueError, TypeError):
                    pass

    process_count = len(matching_pids)
    running = process_count > 0

    if running:
        taskbar_impact = "none"
        desktop_impact = "none"
        status_str = "healthy"
        severity = Severity.INFO
        title = "Windows Explorer process is running"
        description = (
            f"Windows Explorer (explorer.exe) is running with {process_count} process record(s) "
            f"(PIDs: {matching_pids}). Process presence is supporting evidence for shell functionality."
        )
    else:
        taskbar_impact = "likely_affected"
        desktop_impact = "likely_affected"
        status_str = "warning"
        severity = Severity.WARNING
        title = "Windows Explorer is not running"
        description = (
            "Windows Explorer (explorer.exe) is not running. The taskbar, Start menu, and desktop icons "
            "may be unavailable."
        )
        warnings.append("Windows Explorer process is not running.")

    data = {
        "kind": KIND_EXPLORER_DIAGNOSIS,
        "process_name": TARGET_PROCESS_NAME,
        "running": running,
        "process_count": process_count,
        "process_ids": matching_pids,
        "taskbar_impact": taskbar_impact,
        "desktop_impact": desktop_impact,
        "status": status_str,
        "warnings": warnings,
        "limitations": limitations,
    }

    return Evidence(
        category=EvidenceCategory.EXPLORER,
        severity=severity,
        title=title,
        description=description,
        source="diagnose_explorer",
        data=data,
    )
