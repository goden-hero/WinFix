"""Bounded, safe temporary file cleanup adapter for WinFix Agent.

Cleanup is strictly constrained to a trusted backend-configured canonical root.
No user, API client, or LLM parameter can alter or override this root.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.schemas.actions import ActionId, ExecutionResult


def get_demo_temp_dir() -> Path:
    """Return the canonical, trusted backend root for temporary file cleanup."""
    env_dir = os.getenv("WINFIX_DEMO_TEMP_DIR")
    if env_dir:
        target = Path(env_dir)
    elif os.name == "nt":
        target = Path(r"C:\WinFixDemo\TempJunk")
    else:
        target = Path("/tmp/WinFixDemo/TempJunk")

    resolved = target.resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def measure_temp_dir(root: Path | None = None) -> tuple[int, int]:
    """Measure total file bytes and count inside root without following symlinks."""
    target_root = (root or get_demo_temp_dir()).resolve()
    if not target_root.exists() or not target_root.is_dir():
        return 0, 0

    total_bytes = 0
    file_count = 0

    for current_root, dirs, files in os.walk(target_root, followlinks=False):
        # Do not recurse into symlinked/junction directories
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(current_root, d))]
        for name in files:
            file_path = Path(current_root) / name
            try:
                stat = file_path.stat(follow_symlinks=False)
                total_bytes += stat.st_size
                file_count += 1
            except (OSError, PermissionError):
                continue

    return total_bytes, file_count


def clear_temp_files() -> ExecutionResult:
    """Safely remove files inside the canonical temp root, reporting before/after metrics."""
    trusted_root = get_demo_temp_dir().resolve()

    # Capture BEFORE baseline
    bytes_before, files_before = measure_temp_dir(trusted_root)

    files_deleted = 0
    skipped_items: list[str] = []
    failures: list[str] = []

    def _delete_path(path: Path) -> None:
        nonlocal files_deleted
        # Verify canonical safety boundary before any operation
        try:
            resolved = path.resolve()
            if trusted_root not in resolved.parents and resolved != trusted_root:
                failures.append(f"Security error: path {path} attempts to escape root {trusted_root}")
                return
        except (OSError, RuntimeError):
            failures.append(f"Could not resolve canonical path for {path}")
            return

        # Do not follow symlinks/junctions
        if os.path.islink(path):
            try:
                path.unlink()
                files_deleted += 1
            except (OSError, PermissionError) as err:
                skipped_items.append(f"{path.name} (locked symlink: {err})")
            return

        if path.is_file():
            try:
                path.unlink()
                files_deleted += 1
            except (OSError, PermissionError) as err:
                skipped_items.append(f"{path.name} (file locked/in-use: {err})")
            return

        if path.is_dir():
            for child in list(path.iterdir()):
                _delete_path(child)
            try:
                path.rmdir()
            except (OSError, PermissionError) as err:
                skipped_items.append(f"{path.name} (directory in-use: {err})")

    # Iterate direct children of trusted root
    if trusted_root.exists() and trusted_root.is_dir():
        for child_item in list(trusted_root.iterdir()):
            _delete_path(child_item)

    # Capture AFTER baseline
    bytes_after, files_after = measure_temp_dir(trusted_root)
    bytes_reclaimed = max(0, bytes_before - bytes_after)

    details: dict[str, Any] = {
        "target_directory": str(trusted_root),
        "bytes_before": bytes_before,
        "file_count_before": files_before,
        "bytes_after": bytes_after,
        "file_count_after": files_after,
        "files_deleted": files_deleted,
        "bytes_reclaimed": bytes_reclaimed,
        "skipped_items": skipped_items,
        "failures": failures,
    }

    if failures:
        status = "failed"
        message = f"Encountered security or resolution errors during cleanup of {trusted_root}."
    elif skipped_items:
        status = "partial_success"
        message = f"Cleaned {files_deleted} files ({bytes_reclaimed} bytes reclaimed). {len(skipped_items)} item(s) were locked or skipped."
    else:
        status = "success"
        message = f"Successfully cleaned temporary directory {trusted_root}. Reclaimed {bytes_reclaimed} bytes across {files_deleted} files."

    return ExecutionResult(
        action_id=ActionId.CLEAR_TEMP_FILES,
        status=status,
        message=message,
        details=details,
    )
