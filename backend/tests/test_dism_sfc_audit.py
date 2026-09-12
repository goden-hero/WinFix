from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.executor.winutil_adapter import NativeWindowsAdapter
from app.schemas.actions import ActionId


def test_dism_command_is_checkhealth_diagnostic_only():
    adapter = NativeWindowsAdapter()
    with patch("app.executor.winutil_adapter.is_windows_admin", return_value=True), \
         patch("platform.system", return_value="Windows"), \
         patch("subprocess.run") as mock_sub:

        mock_sub.return_value = MagicMock(returncode=0, stdout="The component store is repairable.", stderr="")

        res = adapter.execute(ActionId.RUN_DISM_HEALTH_CHECK, {})

        assert res.status == "success"
        mock_sub.assert_called_once()
        args, kwargs = mock_sub.call_args
        cmd = args[0]

        # Verify exact command arguments
        assert cmd == ["Dism.exe", "/Online", "/Cleanup-Image", "/CheckHealth"]
        # Verify /RestoreHealth is NEVER invoked
        assert "/RestoreHealth" not in cmd


def test_dism_error_740_returns_requires_elevation_not_success():
    adapter = NativeWindowsAdapter()
    with patch("app.executor.winutil_adapter.is_windows_admin", return_value=True), \
         patch("platform.system", return_value="Windows"), \
         patch("subprocess.run") as mock_sub:

        mock_sub.return_value = MagicMock(returncode=740, stdout="Error: 740 Elevated permissions are required to run DISM.", stderr="")

        res = adapter.execute(ActionId.RUN_DISM_HEALTH_CHECK, {})

        assert res.status == "requires_elevation"
        assert res.status != "success"
        assert res.status != "failed"
        assert res.status != "partially_solved"


def test_sfc_error_740_returns_requires_elevation_not_success():
    adapter = NativeWindowsAdapter()
    with patch("app.executor.winutil_adapter.is_windows_admin", return_value=True), \
         patch("platform.system", return_value="Windows"), \
         patch("subprocess.run") as mock_sub:

        mock_sub.return_value = MagicMock(returncode=1, stdout="You must be an administrator running a console session to use the sfc utility.", stderr="")

        res = adapter.execute(ActionId.RUN_SFC_SCAN, {})

        assert res.status == "requires_elevation"
        assert res.status != "success"
