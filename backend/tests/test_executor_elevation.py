from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from app.executor.executor import ControlledExecutor
from app.executor.registry import ActionRegistry
from app.safety.validator import ActionValidationError
from app.schemas.actions import ActionId, RecommendedAction


@pytest.fixture
def mock_adapter():
    return MagicMock()


@pytest.fixture
def executor(mock_adapter):
    registry = ActionRegistry()
    return ControlledExecutor(registry=registry, adapter=mock_adapter)


def test_non_admin_sfc_blocked_before_adapter_and_subprocess(executor, mock_adapter):
    rec = RecommendedAction(action_id=ActionId.RUN_SFC_SCAN, reason="Test SFC scan")
    with patch("app.executor.executor.is_windows_admin", return_value=False), patch("subprocess.run") as mock_sub:
        res = executor.execute(rec, approved=True)

        assert res.status == "requires_elevation"
        assert "requires Administrator privileges" in res.message
        assert res.action_id == ActionId.RUN_SFC_SCAN

        # Proves NativeWindowsAdapter is NEVER called when elevation is unavailable
        mock_adapter.execute.assert_not_called()
        # Proves Subprocess is NEVER called when blocked
        mock_sub.assert_not_called()


def test_non_admin_dism_blocked_before_adapter_and_subprocess(executor, mock_adapter):
    rec = RecommendedAction(action_id=ActionId.RUN_DISM_HEALTH_CHECK, reason="Test DISM health check")
    with patch("app.executor.executor.is_windows_admin", return_value=False), patch("subprocess.run") as mock_sub:
        res = executor.execute(rec, approved=True)

        assert res.status == "requires_elevation"
        assert "requires Administrator privileges" in res.message
        assert res.action_id == ActionId.RUN_DISM_HEALTH_CHECK

        # Proves NativeWindowsAdapter is NEVER called when elevation is unavailable
        mock_adapter.execute.assert_not_called()
        # Proves Subprocess is NEVER called when blocked
        mock_sub.assert_not_called()


def test_admin_privileges_do_not_bypass_user_approval(executor, mock_adapter):
    rec = RecommendedAction(action_id=ActionId.RUN_SFC_SCAN, reason="Test SFC scan without approval")
    with patch("app.executor.executor.is_windows_admin", return_value=True):
        with pytest.raises(ActionValidationError) as exc_info:
            executor.execute(rec, approved=False)

        assert "blocked by safety policy" in str(exc_info.value)
        # Proves adapter and subprocess are never called when approval is False even with admin
        mock_adapter.execute.assert_not_called()


def test_unimplemented_actions_never_reach_adapter(executor, mock_adapter):
    rec_privacy = RecommendedAction(action_id=ActionId.APPLY_PRIVACY_PROFILE, reason="Test privacy profile", parameters={"profile": "balanced"})
    rec_optional = RecommendedAction(action_id=ActionId.REMOVE_OPTIONAL_APP, reason="Test remove app", parameters={"package_id": "demo"})

    res1 = executor.execute(rec_privacy, approved=True)
    assert res1.status == "not_implemented"
    assert res1.action_id == ActionId.APPLY_PRIVACY_PROFILE

    res2 = executor.execute(rec_optional, approved=True)
    assert res2.status == "not_implemented"
    assert res2.action_id == ActionId.REMOVE_OPTIONAL_APP

    # Proves unimplemented actions never reach the adapter
    mock_adapter.execute.assert_not_called()
