from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
from app.schemas.actions import ActionId, RecommendedAction
from app.schemas.diagnosis import DiagnosisResult
from app.schemas.session import CreateSessionRequest, SessionStatus
from app.schemas.verification import VerificationStatus
from app.services.session_service import SessionService


@pytest.fixture
def session_service():
    return SessionService()


@pytest.mark.asyncio
async def test_requires_elevation_maps_to_verification_status(session_service):
    session = session_service.create(CreateSessionRequest(user_problem="System files corrupt"))

    diag = DiagnosisResult(
        summary="Corrupt files found",
        overall_confidence=0.9,
        recommended_actions=[
            RecommendedAction(action_id=ActionId.RUN_SFC_SCAN, reason="Scan system files")
        ],
    )

    with patch.object(session_service.agent, "investigate", return_value=([], diag)):
        diagnosed = await session_service.diagnose(session.session_id, MagicMock(categories=["system_health"]))

    approved = session_service.approve(diagnosed.session_id, {"decisions": [{"action_id": ActionId.RUN_SFC_SCAN, "approved": True}]})

    with patch("app.executor.executor.is_windows_admin", return_value=False):
        executed = session_service.execute(approved.session_id)

    assert len(executed.execution_results) == 1
    assert executed.execution_results[0].status == "requires_elevation"

    verified = session_service.verify(executed.session_id)
    assert len(verified.verification_results) == 1
    v_res = verified.verification_results[0]
    assert v_res.status == VerificationStatus.REQUIRES_ELEVATION
    assert "requires Administrator privileges" in v_res.summary
    assert verified.status == SessionStatus.COMPLETED


@pytest.mark.asyncio
async def test_not_implemented_maps_to_verification_status(session_service):
    session = session_service.create(CreateSessionRequest(user_problem="Remove optional software"))

    diag = DiagnosisResult(
        summary="Optional software found",
        overall_confidence=0.8,
        recommended_actions=[
            RecommendedAction(action_id=ActionId.REMOVE_OPTIONAL_APP, reason="Remove app", parameters={"package_id": "demo"})
        ],
    )

    with patch.object(session_service.agent, "investigate", return_value=([], diag)):
        diagnosed = await session_service.diagnose(session.session_id, MagicMock(categories=["performance"]))

    approved = session_service.approve(diagnosed.session_id, {"decisions": [{"action_id": ActionId.REMOVE_OPTIONAL_APP, "approved": True}]})

    executed = session_service.execute(approved.session_id)

    assert len(executed.execution_results) == 1
    assert executed.execution_results[0].status == "not_implemented"

    verified = session_service.verify(executed.session_id)
    assert len(verified.verification_results) == 1
    v_res = verified.verification_results[0]
    assert v_res.status == VerificationStatus.NOT_IMPLEMENTED
    assert "intentionally disabled" in v_res.summary
