"""Tests for safety hardening, controlled execution boundaries, and fail-closed policies."""

from __future__ import annotations

from unittest.mock import patch
import pytest

from app.executor.winutil_adapter import NativeWindowsAdapter
from app.executor.startup_manager import disable_startup_app
from app.schemas.actions import ActionId


def test_dism_health_check_uses_fixed_array_args():
    """Verify DISM health check executes strictly read-only CheckHealth with shell=False."""
    adapter = NativeWindowsAdapter()
    with patch("app.executor.winutil_adapter.is_windows_admin", return_value=True), \
         patch("platform.system", return_value="Windows"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "No component store corruption detected."

        result = adapter.execute(ActionId.RUN_DISM_HEALTH_CHECK, {})

        if mock_run.called:
            args, kwargs = mock_run.call_args
            assert args[0] == ["Dism.exe", "/Online", "/Cleanup-Image", "/CheckHealth"]
            assert kwargs.get("shell") is False
        assert result.status == "success"


def test_sfc_scan_uses_fixed_array_args():
    """Verify SFC scan executes strictly verifyonly with shell=False."""
    adapter = NativeWindowsAdapter()
    with patch("app.executor.winutil_adapter.is_windows_admin", return_value=True), \
         patch("platform.system", return_value="Windows"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Windows Resource Protection did not find any integrity violations."

        result = adapter.execute(ActionId.RUN_SFC_SCAN, {})

        if mock_run.called:
            args, kwargs = mock_run.call_args
            assert args[0] == ["sfc.exe", "/verifyonly"]
            assert kwargs.get("shell") is False
        assert result.status == "success"


def test_privacy_profile_returns_not_implemented():
    """Verify APPLY_PRIVACY_PROFILE is intentionally disabled in MVP and returns not_implemented."""
    adapter = NativeWindowsAdapter()
    result = adapter.execute(ActionId.APPLY_PRIVACY_PROFILE, {"profile": "balanced"})
    assert result.status == "not_implemented"
    assert "disabled" in result.message.lower()


def test_remove_optional_app_returns_not_implemented():
    """Verify REMOVE_OPTIONAL_APP is intentionally disabled in MVP and returns not_implemented."""
    adapter = NativeWindowsAdapter()
    result = adapter.execute(ActionId.REMOVE_OPTIONAL_APP, {"package_id": "test_pkg"})
    assert result.status == "not_implemented"
    assert "disabled" in result.message.lower()


def test_startup_app_requires_hkcu_run_prefix():
    """Verify invalid startup identifiers without hkcu_run: prefix raise ValueError."""
    from app.diagnostics.startup import parse_startup_entry_id
    with pytest.raises(ValueError, match="hkcu_run:"):
        parse_startup_entry_id("hklm_run:SomeApp")
