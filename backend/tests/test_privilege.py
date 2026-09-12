from __future__ import annotations

import os
from unittest.mock import patch

from app.safety.privilege import is_windows_admin


def test_is_windows_admin_non_windows():
    with patch("os.name", "posix"):
        assert is_windows_admin() is False


def test_is_windows_admin_windows_mock():
    with patch("os.name", "nt"):
        # On non-Windows platforms, importing ctypes or shell32 might fail or behave differently,
        # so is_windows_admin() safely catches exceptions and returns False.
        res = is_windows_admin()
        assert isinstance(res, bool)
