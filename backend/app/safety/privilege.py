"""Windows privilege detection layer for WinFix.

Read-only detection of process elevation.
No elevation attempt, no UAC bypass, no privilege escalation.
"""

from __future__ import annotations

import os


def is_windows_admin() -> bool:
    """Check if the current process is running with Windows Administrator privileges.

    Returns False safely on non-Windows operating systems or if the check fails.
    """
    if os.name != "nt":
        return False
    try:
        import ctypes

        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False
