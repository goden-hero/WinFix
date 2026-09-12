"""Read-only Windows Update diagnostic module for WinFix Agent.

Collects structured evidence for:
- Windows Update core service statuses (wuauserv, BITS, CryptSvc)
- Pending reboot indicators via read-only registry checks
- Windows Update download cache directory metadata

Operates cleanly across Windows and non-Windows systems using dependency injection for complete test isolation without modifying any system state.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path, PureWindowsPath, UnsupportedOperation
import platform
from typing import Any, Callable

from app.schemas.evidence import Evidence, EvidenceCategory, Severity


FIXED_WINDOWS_UPDATE_SERVICES = ["wuauserv", "BITS", "CryptSvc"]
SERVICE_DISPLAY_NAMES = {
    "wuauserv": "Windows Update Service",
    "BITS": "Background Intelligent Transfer Service",
    "CryptSvc": "Cryptographic Services",
}


def default_service_checker(service_name: str) -> dict[str, Any]:
    """Check service status and startup type using native Windows APIs / psutil / winreg."""
    if platform.system() != "Windows" or os.name != "nt":
        return {
            "name": service_name,
            "display_name": SERVICE_DISPLAY_NAMES.get(service_name, service_name),
            "status": "unavailable",
            "startup_type": "unknown",
            "is_running": False,
            "error": "Service inspection is not supported on non-Windows platforms.",
        }

    display_name = SERVICE_DISPLAY_NAMES.get(service_name, service_name)
    startup_type = "unknown"
    status = "unavailable"
    is_running = False
    error = None

    # 1. Query startup type via HKLM Services registry key if possible
    try:
        import winreg
        key_path = rf"SYSTEM\CurrentControlSet\Services\{service_name}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ) as key:
            start_val, _ = winreg.QueryValueEx(key, "Start")
            if start_val == 2:
                startup_type = "automatic"
            elif start_val == 3:
                startup_type = "manual"
            elif start_val == 4:
                startup_type = "disabled"
            elif start_val in (0, 1):
                startup_type = "boot_system"
    except (PermissionError, OSError, ImportError) as err:
        error = f"Registry query error for {service_name}: {err}"

    # 2. Query running status via psutil
    try:
        import psutil
        try:
            svc = psutil.win_service_get(service_name)
            svc_info = svc.as_dict()
            status_str = str(svc_info.get("status", "")).lower()
            if status_str == "running":
                status = "running"
                is_running = True
            elif status_str == "stopped":
                status = "stopped"
                is_running = False
            else:
                status = status_str or "unknown"
                is_running = False

            if startup_type == "disabled" and status == "stopped":
                status = "disabled"
        except psutil.NoSuchProcess:
            status = "missing"
            is_running = False
            error = f"Service '{service_name}' was not found on this system."
    except Exception as err:
        if not error:
            error = f"Service query error for {service_name}: {err}"

    return {
        "name": service_name,
        "display_name": display_name,
        "status": status,
        "startup_type": startup_type,
        "is_running": is_running,
        "error": error,
    }


def default_registry_reader() -> tuple[bool | None, list[str], str | None]:
    """Check read-only Windows registry locations for pending reboot indicators."""
    if platform.system() != "Windows" or os.name != "nt":
        return None, [], "Registry reboot checks are not supported on non-Windows platforms."

    reboot_reasons: list[str] = []
    error_message: str | None = None

    try:
        import winreg

        # Key 1: CBS RebootPending
        cbs_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cbs_path, 0, winreg.KEY_READ):
                reboot_reasons.append("CBS RebootPending registry key exists")
        except FileNotFoundError:
            pass
        except (PermissionError, OSError) as err:
            error_message = f"Permission error reading CBS RebootPending: {err}"

        # Key 2: WindowsUpdate RebootRequired
        wu_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, wu_path, 0, winreg.KEY_READ):
                reboot_reasons.append("WindowsUpdate RebootRequired registry key exists")
        except FileNotFoundError:
            pass
        except (PermissionError, OSError) as err:
            if not error_message:
                error_message = f"Permission error reading RebootRequired: {err}"

        # Key 3: PendingFileRenameOperations
        sm_path = r"SYSTEM\CurrentControlSet\Control\Session Manager"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sm_path, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "PendingFileRenameOperations")
                if val:
                    reboot_reasons.append("PendingFileRenameOperations registry value exists")
        except FileNotFoundError:
            pass
        except (PermissionError, OSError) as err:
            if not error_message:
                error_message = f"Permission error reading PendingFileRenameOperations: {err}"

    except (ImportError, Exception) as err:
        error_message = f"Unexpected error checking reboot registry keys: {err}"
        return None, [], error_message

    if error_message and not reboot_reasons:
        return None, [], error_message

    pending = len(reboot_reasons) > 0
    return pending, reboot_reasons, error_message


def default_directory_checker(target_path: Any) -> tuple[bool, bool, int, int, str | None]:
    """Check existence, accessibility, total bytes, and file count of directory without modifying files."""
    try:
        try:
            resolved = target_path.resolve()
        except (AttributeError, UnsupportedOperation, NotImplementedError):
            resolved = target_path

        path_str = str(resolved)
        if not os.path.exists(path_str):
            return False, False, 0, 0, None

        if not os.path.isdir(path_str):
            return True, False, 0, 0, f"Path '{target_path}' exists but is not a directory."

        total_bytes = 0
        file_count = 0
        accessible = True

        for root, dirs, files in os.walk(path_str, followlinks=False):
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    stat = os.stat(file_path, follow_symlinks=False)
                    total_bytes += stat.st_size
                    file_count += 1
                except (OSError, PermissionError):
                    continue

        return True, accessible, total_bytes, file_count, None
    except (PermissionError, OSError) as err:
        return True, False, 0, 0, f"Access error reading directory '{target_path}': {err}"


def diagnose_windows_update(
    service_checker: Callable[[str], dict[str, Any]] | None = None,
    registry_reader: Callable[[], tuple[bool | None, list[str], str | None]] | None = None,
    directory_checker: Callable[[Path], tuple[bool, bool, int, int, str | None]] | None = None,
    system_root: Path | None = None,
) -> list[Evidence]:
    """Collect read-only structured evidence for Windows Update health and readiness."""
    svc_fn = service_checker or default_service_checker
    reg_fn = registry_reader or default_registry_reader
    dir_fn = directory_checker or default_directory_checker

    is_windows = platform.system() == "Windows" and os.name == "nt"
    evidence_list: list[Evidence] = []
    now = datetime.now(timezone.utc)

    # 1. Services Diagnostics
    service_data: dict[str, Any] = {}
    stopped_or_disabled: list[str] = []
    missing_or_err: list[str] = []

    for svc_name in FIXED_WINDOWS_UPDATE_SERVICES:
        res = svc_fn(svc_name)
        service_data[svc_name] = res
        if res["status"] in ("stopped", "disabled"):
            stopped_or_disabled.append(f"{res['display_name']} ({res['status']})")
        elif res["status"] in ("unavailable", "missing") or res.get("error"):
            missing_or_err.append(f"{res['display_name']} ({res['status']})")

    wuauserv_status = service_data.get("wuauserv", {}).get("status")
    if not is_windows:
        svc_severity = Severity.INFO
        svc_health = "not_applicable"
        svc_desc = "Windows Update service checks are not applicable on non-Windows operating systems."
        evidence_quality = "low"
    elif wuauserv_status in ("stopped", "disabled", "missing"):
        svc_severity = Severity.CRITICAL
        svc_health = "problem_detected"
        svc_desc = f"Windows Update services issue detected: {', '.join(stopped_or_disabled + missing_or_err)}."
        evidence_quality = "high"
    elif stopped_or_disabled or missing_or_err:
        svc_severity = Severity.WARNING
        svc_health = "warning"
        svc_desc = f"Windows Update services issue detected: {', '.join(stopped_or_disabled + missing_or_err)}."
        evidence_quality = "high"
    else:
        svc_severity = Severity.INFO
        svc_health = "healthy"
        svc_desc = "All core Windows Update services (wuauserv, BITS, CryptSvc) are active and running."
        evidence_quality = "high"

    evidence_list.append(
        Evidence(
            category=EvidenceCategory.WINDOWS_UPDATE,
            severity=svc_severity,
            title="Windows Update core services",
            description=svc_desc,
            source="windows_services",
            timestamp=now,
            data={
                "platform": platform.system(),
                "is_windows": is_windows,
                "overall_service_health": svc_health,
                "services": service_data,
                "evidence_quality": evidence_quality,
                "collected_at": now.isoformat(),
            },
        )
    )

    # 2. Pending Reboot Diagnostics
    pending_reboot, reboot_reasons, reg_error = reg_fn()

    if not is_windows:
        reboot_status_str = "NOT_APPLICABLE"
        reboot_severity = Severity.INFO
        reboot_desc = "Pending reboot inspection is not applicable on non-Windows operating systems."
        reboot_quality = "low"
    elif pending_reboot is True:
        reboot_status_str = "REBOOT_PENDING"
        reboot_severity = Severity.WARNING
        reboot_desc = f"System requires a reboot before Windows Update can complete: {'; '.join(reboot_reasons)}."
        reboot_quality = "high"
    elif pending_reboot is False:
        reboot_status_str = "NO_REBOOT_PENDING"
        reboot_severity = Severity.INFO
        reboot_desc = "No pending system reboot was detected in Windows registry."
        reboot_quality = "high"
    else:
        reboot_status_str = "UNKNOWN"
        reboot_severity = Severity.WARNING
        reboot_desc = f"Could not conclusively determine pending reboot status: {reg_error or 'Registry read unavailable'}."
        reboot_quality = "medium"

    evidence_list.append(
        Evidence(
            category=EvidenceCategory.WINDOWS_UPDATE,
            severity=reboot_severity,
            title="Windows Update pending reboot status",
            description=reboot_desc,
            source="windows_registry",
            timestamp=now,
            data={
                "platform": platform.system(),
                "pending_reboot": pending_reboot,
                "status": reboot_status_str,
                "reboot_reasons": reboot_reasons,
                "error_message": reg_error,
                "evidence_quality": reboot_quality,
                "collected_at": now.isoformat(),
            },
        )
    )

    # 3. Download Cache Directory Diagnostics
    if not is_windows:
        cache_path = PureWindowsPath(r"C:\Windows\SoftwareDistribution\Download")
        exists, accessible, bytes_size, file_count, cache_err = False, False, 0, 0, None
    else:
        try:
            target_root = system_root if system_root else Path(os.environ.get("SystemRoot", r"C:\Windows"))
            cache_path = target_root / "SoftwareDistribution" / "Download"
            exists, accessible, bytes_size, file_count, cache_err = dir_fn(cache_path)
        except (UnsupportedOperation, NotImplementedError, Exception):
            cache_path = PureWindowsPath(r"C:\Windows\SoftwareDistribution\Download")
            exists, accessible, bytes_size, file_count, cache_err = dir_fn(cache_path)

    if not is_windows:
        cache_desc = "Windows Update cache inspection is not applicable on non-Windows operating systems."
        cache_severity = Severity.INFO
        cache_quality = "low"
    elif not exists:
        cache_desc = f"Windows Update download cache directory '{cache_path}' does not exist."
        cache_severity = Severity.WARNING
        cache_quality = "high"
    elif not accessible or cache_err:
        cache_desc = f"Windows Update download cache directory '{cache_path}' exists but access failed: {cache_err}."
        cache_severity = Severity.WARNING
        cache_quality = "medium"
    else:
        mb_size = round(bytes_size / (1024 * 1024), 2)
        cache_desc = f"Windows Update download cache contains {file_count} files ({mb_size} MB) at '{cache_path}'."
        cache_severity = Severity.INFO
        cache_quality = "high"

    evidence_list.append(
        Evidence(
            category=EvidenceCategory.WINDOWS_UPDATE,
            severity=cache_severity,
            title="Windows Update download cache",
            description=cache_desc,
            source="filesystem",
            timestamp=now,
            data={
                "platform": platform.system(),
                "target_directory": str(cache_path),
                "cache_exists": exists,
                "cache_accessible": accessible,
                "cache_size_bytes": bytes_size,
                "file_count": file_count,
                "error_message": cache_err,
                "evidence_quality": cache_quality,
                "collected_at": now.isoformat(),
            },
        )
    )

    return evidence_list
