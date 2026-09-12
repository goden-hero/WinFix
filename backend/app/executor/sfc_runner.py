"""Bounded, controlled executor adapter for Windows System File Checker (sfc.exe /scannow).

Guarantees fixed command execution with no caller-controlled paths or arguments.
Uses dependency injection for process execution and elevation checks to support test isolation without global environment variables.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import subprocess
import threading
from typing import Callable, Any

from app.executor.sfc_parser import SfcParsedStatus, parse_sfc_output
from app.schemas.actions import ActionId, ExecutionResult

DEFAULT_TIMEOUT_SECONDS = 300.0


from app.safety.privilege import is_windows_admin

check_windows_admin = is_windows_admin


def default_process_runner(executable: str, args: list[str], timeout: float) -> tuple[int, str, str]:
    """Execute fixed command without shell=True."""
    proc = subprocess.run(
        [executable] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


class SfcRunner:
    """Controlled SFC executor ensuring fixed execution of 'sfc.exe /scannow'."""

    def __init__(
        self,
        process_runner: Callable[[str, list[str], float], tuple[int, str, str]] | None = None,
        admin_checker: Callable[[], bool] | None = None,
        sfc_path: Path | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._runner = process_runner or default_process_runner
        self._admin_checker = admin_checker or check_windows_admin
        self._sfc_path = sfc_path
        self._timeout = timeout_seconds
        self._lock = threading.Lock()

    def _resolve_sfc_executable(self) -> Path | None:
        if self._sfc_path:
            return self._sfc_path if self._sfc_path.exists() else None

        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        candidate = Path(system_root) / "System32" / "sfc.exe"
        if candidate.is_file():
            return candidate

        # Fallback resolution on Windows PATH if System32 path doesn't exist directly
        if os.name == "nt":
            import shutil
            found = shutil.which("sfc.exe")
            if found:
                return Path(found)

        return None

    def execute(self) -> ExecutionResult:
        """Execute sfc.exe /scannow with strict bounds and lock protection."""
        if not self._lock.acquire(blocking=False):
            return ExecutionResult(
                action_id=ActionId.RUN_SFC_SCAN,
                status="failed",
                message="An SFC scan operation is already in progress.",
                details={
                    "command": "sfc.exe /scannow",
                    "parsed_status": SfcParsedStatus.EXECUTION_FAILED.value,
                    "reason": "concurrent_execution_blocked",
                },
            )

        try:
            return self._execute_internal()
        finally:
            self._lock.release()

    def _execute_internal(self) -> ExecutionResult:
        start_time = datetime.now(timezone.utc)

        # 1. Platform validation
        if platform.system() != "Windows" and os.name != "nt":
            end_time = datetime.now(timezone.utc)
            return ExecutionResult(
                action_id=ActionId.RUN_SFC_SCAN,
                status="failed",
                message="SFC scan is only supported on Windows systems.",
                details={
                    "command": "sfc.exe /scannow",
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": round((end_time - start_time).total_seconds(), 2),
                    "parsed_status": SfcParsedStatus.EXECUTION_FAILED.value,
                    "corruption_found": None,
                    "repaired": None,
                    "reason": "unsupported_platform",
                },
            )

        # 2. Executable resolution
        sfc_exe = self._resolve_sfc_executable()
        if not sfc_exe:
            end_time = datetime.now(timezone.utc)
            return ExecutionResult(
                action_id=ActionId.RUN_SFC_SCAN,
                status="failed",
                message="sfc.exe executable was not found on this system.",
                details={
                    "command": "sfc.exe /scannow",
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": round((end_time - start_time).total_seconds(), 2),
                    "parsed_status": SfcParsedStatus.EXECUTION_FAILED.value,
                    "corruption_found": None,
                    "repaired": None,
                    "reason": "missing_executable",
                },
            )

        # 3. Privilege / elevation validation
        if not self._admin_checker():
            end_time = datetime.now(timezone.utc)
            return ExecutionResult(
                action_id=ActionId.RUN_SFC_SCAN,
                status="requires_elevation",
                message="Administrator privileges are required to run SFC scan.",
                details={
                    "command": "sfc.exe /scannow",
                    "executable": str(sfc_exe),
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": round((end_time - start_time).total_seconds(), 2),
                    "parsed_status": SfcParsedStatus.PERMISSION_DENIED.value,
                    "corruption_found": None,
                    "repaired": None,
                    "reason": "elevation_required",
                },
            )

        # 4. Fixed execution
        try:
            exit_code, stdout, stderr = self._runner(str(sfc_exe), ["/scannow"], self._timeout)
            end_time = datetime.now(timezone.utc)
            duration = round((end_time - start_time).total_seconds(), 2)

            parse_res = parse_sfc_output(stdout, stderr, exit_code)

            if parse_res.status in {SfcParsedStatus.NO_CORRUPTION_FOUND, SfcParsedStatus.CORRUPTION_REPAIRED}:
                exec_status = "success"
            elif parse_res.status == SfcParsedStatus.CORRUPTION_FOUND_NOT_REPAIRED:
                exec_status = "partial_success"
            else:
                exec_status = "failed"

            return ExecutionResult(
                action_id=ActionId.RUN_SFC_SCAN,
                status=exec_status,
                message=parse_res.message,
                details={
                    "command": "sfc.exe /scannow",
                    "executable": str(sfc_exe),
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "parsed_status": parse_res.status.value,
                    "corruption_found": parse_res.corruption_found,
                    "repaired": parse_res.repaired,
                    "cbs_log_path": r"C:\Windows\Logs\CBS\CBS.log",
                },
            )

        except subprocess.TimeoutExpired:
            end_time = datetime.now(timezone.utc)
            duration = round((end_time - start_time).total_seconds(), 2)
            return ExecutionResult(
                action_id=ActionId.RUN_SFC_SCAN,
                status="failed",
                message=f"SFC scan operation timed out after {self._timeout} seconds.",
                details={
                    "command": "sfc.exe /scannow",
                    "executable": str(sfc_exe),
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "parsed_status": SfcParsedStatus.TIMEOUT.value,
                    "corruption_found": None,
                    "repaired": None,
                    "reason": "timeout",
                },
            )
        except Exception as err:
            end_time = datetime.now(timezone.utc)
            duration = round((end_time - start_time).total_seconds(), 2)
            return ExecutionResult(
                action_id=ActionId.RUN_SFC_SCAN,
                status="failed",
                message=f"Failed to launch SFC process: {err}",
                details={
                    "command": "sfc.exe /scannow",
                    "executable": str(sfc_exe),
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "parsed_status": SfcParsedStatus.EXECUTION_FAILED.value,
                    "corruption_found": None,
                    "repaired": None,
                    "reason": str(err),
                },
            )
