"""Pure, unit-testable parser for Windows System File Checker (SFC /scannow) output.

Parses stdout and stderr to classify the scan outcome without relying solely on exit code.
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple


class SfcParsedStatus(str, Enum):
    NO_CORRUPTION_FOUND = "no_corruption_found"
    CORRUPTION_REPAIRED = "corruption_repaired"
    CORRUPTION_FOUND_NOT_REPAIRED = "corruption_found_not_repaired"
    EXECUTION_FAILED = "execution_failed"
    PERMISSION_DENIED = "permission_denied"
    TIMEOUT = "timeout"
    UNKNOWN_RESULT = "unknown_result"


class SfcParseResult(NamedTuple):
    status: SfcParsedStatus
    message: str
    corruption_found: bool | None
    repaired: bool | None


# Canonical English SFC output phrases (case-insensitive search)
PHRASES_NO_CORRUPTION = [
    "did not find any integrity violations",
    "no integrity violations",
]

PHRASES_REPAIRED = [
    "found corrupt files and successfully repaired them",
    "corrupt files and successfully repaired",
]

PHRASES_NOT_REPAIRED = [
    "found corrupt files but was unable to fix some of them",
    "unable to fix some of them",
    "could not fix some of them",
]

PHRASES_OPERATION_FAILED = [
    "could not perform the requested operation",
    "failed to perform the requested operation",
]

PHRASES_PERMISSION_DENIED = [
    "must be an administrator running a console session",
    "access is denied",
    "requires elevation",
    "administrator privileges required",
]


def parse_sfc_output(stdout: str | None, stderr: str | None, exit_code: int | None = None) -> SfcParseResult:
    """Parse SFC stdout, stderr, and optional exit code into a structured result."""
    stdout_clean = (stdout or "").strip()
    stderr_clean = (stderr or "").strip()
    combined_text = f"{stdout_clean}\n{stderr_clean}".strip().lower()

    if not combined_text:
        return SfcParseResult(
            status=SfcParsedStatus.UNKNOWN_RESULT,
            message="SFC output was empty.",
            corruption_found=None,
            repaired=None,
        )

    # 1. Check permission/elevation denied phrases
    for phrase in PHRASES_PERMISSION_DENIED:
        if phrase in combined_text:
            return SfcParseResult(
                status=SfcParsedStatus.PERMISSION_DENIED,
                message="Administrator privileges are required to run SFC scan.",
                corruption_found=None,
                repaired=None,
            )

    # 2. Check operation failed phrases
    for phrase in PHRASES_OPERATION_FAILED:
        if phrase in combined_text:
            return SfcParseResult(
                status=SfcParsedStatus.EXECUTION_FAILED,
                message="Windows Resource Protection could not perform the requested operation.",
                corruption_found=None,
                repaired=None,
            )

    # 3. Check corruption repaired
    for phrase in PHRASES_REPAIRED:
        if phrase in combined_text:
            return SfcParseResult(
                status=SfcParsedStatus.CORRUPTION_REPAIRED,
                message="Windows Resource Protection found corrupt files and successfully repaired them.",
                corruption_found=True,
                repaired=True,
            )

    # 4. Check corruption found but not repaired
    for phrase in PHRASES_NOT_REPAIRED:
        if phrase in combined_text:
            return SfcParseResult(
                status=SfcParsedStatus.CORRUPTION_FOUND_NOT_REPAIRED,
                message="Windows Resource Protection found corrupt files but was unable to fix some of them.",
                corruption_found=True,
                repaired=False,
            )

    # 5. Check no corruption found
    for phrase in PHRASES_NO_CORRUPTION:
        if phrase in combined_text:
            return SfcParseResult(
                status=SfcParsedStatus.NO_CORRUPTION_FOUND,
                message="Windows Resource Protection did not find any integrity violations.",
                corruption_found=False,
                repaired=False,
            )

    # 6. Fallback based on exit code if output does not contain standard phrases
    if exit_code is not None and exit_code != 0:
        return SfcParseResult(
            status=SfcParsedStatus.EXECUTION_FAILED,
            message=f"SFC command exited with error code {exit_code}.",
            corruption_found=None,
            repaired=None,
        )

    return SfcParseResult(
        status=SfcParsedStatus.UNKNOWN_RESULT,
        message="SFC output contained unrecognized content.",
        corruption_found=None,
        repaired=None,
    )
