"""Tests for action execution and verification flow across all ActionIds."""

from __future__ import annotations

import pytest

from app.executor.winutil_adapter import NativeWindowsAdapter
from app.schemas.actions import ActionId
from app.schemas.session import CreateSessionRequest, DiagnoseRequest
from app.schemas.verification import VerificationStatus
from app.services.session_service import SessionService


def test_native_windows_adapter_executes_all_actions():
    """Verify NativeWindowsAdapter returns success for DISM, SFC when elevated, and not_implemented for disabled MVP actions."""
    adapter = NativeWindowsAdapter()

    from unittest.mock import patch, MagicMock

    with patch("app.executor.winutil_adapter.is_windows_admin", return_value=True), \
         patch("platform.system", return_value="Windows"), \
         patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        res_dism = adapter.execute(ActionId.RUN_DISM_HEALTH_CHECK, {})
        assert res_dism.status == "success"
        assert res_dism.action_id == ActionId.RUN_DISM_HEALTH_CHECK

        res_sfc = adapter.execute(ActionId.RUN_SFC_SCAN, {})
        assert res_sfc.status == "success"
        assert res_sfc.action_id == ActionId.RUN_SFC_SCAN

    res_privacy = adapter.execute(ActionId.APPLY_PRIVACY_PROFILE, {"profile": "balanced"})
    assert res_privacy.status == "not_implemented"

    res_app = adapter.execute(ActionId.REMOVE_OPTIONAL_APP, {"package_id": "demo.package"})
    assert res_app.status == "not_implemented"


@pytest.mark.asyncio
async def test_session_execute_and_verify_flow():
    """Verify session approve -> execute -> verify end-to-end flow succeeds."""
    service = SessionService()
    session = service.create(CreateSessionRequest(user_problem="Fix Windows update and system files"))

    # Force mock evidence in session
    session = await service.diagnose(session.session_id, DiagnoseRequest(categories=["performance"]))
    actions = session.diagnosis.recommended_actions if session.diagnosis else []

    if actions:
        decisions = [{"action_id": a.action_id, "approved": True} for a in actions]
        session = service.approve(session.session_id, {"decisions": decisions})

        session = service.execute(session.session_id)
        assert session.status.value == "verifying"

        session = service.verify(session.session_id)
        assert session.status.value == "completed"
        assert len(session.verification_results) == len(actions)
