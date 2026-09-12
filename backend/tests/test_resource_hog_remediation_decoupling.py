from __future__ import annotations

from unittest.mock import patch

import pytest
from app.schemas.actions import ActionId
from app.schemas.evidence import Evidence, EvidenceCategory, Severity
from app.schemas.session import CreateSessionRequest, DiagnoseRequest, SessionStatus
from app.schemas.verification import VerificationStatus
from app.services.session_service import SessionService


@pytest.fixture
def session_service():
    return SessionService()


@pytest.mark.asyncio
async def test_resource_hog_does_not_automatically_recommend_clear_temp_files(session_service):
    """TEST 1: High Chrome/resource usage does NOT automatically recommend CLEAR_TEMP_FILES."""
    session = session_service.create(CreateSessionRequest(user_problem="Chrome is using 80% CPU and 4GB RAM"))

    resource_hog_ev = Evidence(
        category=EvidenceCategory.PERFORMANCE,
        severity=Severity.WARNING,
        title="Top resource consumers",
        description="High CPU/RAM consumers detected.",
        source="winfix_diagnostics",
        data={
            "kind": "RESOURCE_HOG_ANALYSIS",
            "top_resource_consumers": [
                {
                    "name": "Google Chrome",
                    "process_count": 12,
                    "raw_cpu_percent": 80.0,
                    "memory_mb": 4096.0,
                    "impact": "HIGH",
                    "impact_score": 8.5,
                }
            ],
        },
    )

    with patch.object(session_service.agent, "_collect_evidence", return_value=[resource_hog_ev]):
        diagnosed = await session_service.diagnose(session.session_id, DiagnoseRequest(categories=["resource_hog"]))

    recommended_action_ids = [r.action_id for r in diagnosed.diagnosis.recommended_actions]

    # Proves CLEAR_TEMP_FILES is NOT recommended for resource hog
    assert ActionId.CLEAR_TEMP_FILES not in recommended_action_ids
    assert len(recommended_action_ids) == 0

    # Probable cause and finding clearly identify the resource consumer and provide user advice
    cause_titles = [c.title for c in diagnosed.diagnosis.probable_causes]
    assert any("resource consumption" in t.lower() or "chrome" in t.lower() for t in cause_titles)
    cause = diagnosed.diagnosis.probable_causes[0]
    assert "User attention is recommended" in cause.explanation


@pytest.mark.asyncio
async def test_clear_temp_files_only_recommended_with_temp_evidence(session_service):
    """TEST 2: CLEAR_TEMP_FILES is ONLY recommended when temp-file evidence independently supports cleanup."""
    session = session_service.create(CreateSessionRequest(user_problem="Temporary junk files accumulating"))
    temp_ev = Evidence(
        category=EvidenceCategory.PERFORMANCE,
        severity=Severity.WARNING,
        title="Temporary file usage",
        description="High temporary storage usage",
        source="winfix_diagnostics",
        data={"bytes": 500 * 1024**2, "file_count": 1500},
    )
    with patch.object(session_service.agent, "_collect_evidence", return_value=[temp_ev]):
        diagnosed = await session_service.diagnose(session.session_id, DiagnoseRequest(categories=["storage"]))
    recs = [r.action_id for r in diagnosed.diagnosis.recommended_actions]
    assert ActionId.CLEAR_TEMP_FILES in recs


@pytest.mark.asyncio
async def test_full_disk_without_temp_evidence_does_not_recommend_clear_temp_files(session_service):
    """TEST 3: Full system drive (>90%) without temp-file evidence does NOT automatically recommend CLEAR_TEMP_FILES."""
    session = session_service.create(CreateSessionRequest(user_problem="C drive full"))

    disk_ev = Evidence(
        category=EvidenceCategory.PERFORMANCE,
        severity=Severity.WARNING,
        title="System drive capacity",
        description="System drive capacity is at 95%.",
        source="winfix_diagnostics",
        data={"percent": 95, "free_gb": 5, "total_gb": 100},
    )

    with patch.object(session_service.agent, "_collect_evidence", return_value=[disk_ev]):
        diagnosed = await session_service.diagnose(session.session_id, DiagnoseRequest(categories=["storage"]))

    recommended_action_ids = [r.action_id for r in diagnosed.diagnosis.recommended_actions]

    # Disk capacity alone MUST NOT trigger CLEAR_TEMP_FILES
    assert ActionId.CLEAR_TEMP_FILES not in recommended_action_ids
    assert len(recommended_action_ids) == 0

    # Disk capacity is reported as a probable cause / finding with user guidance
    cause_titles = [c.title for c in diagnosed.diagnosis.probable_causes]
    assert any("drive capacity" in t.lower() for t in cause_titles)


@pytest.mark.asyncio
async def test_no_safe_automated_fix_resource_hog(session_service):
    """TEST 4: A resource hog with no implemented remediation does not generate fake actions or fake success."""
    session = session_service.create(CreateSessionRequest(user_problem="Chrome process hogging CPU"))

    resource_hog_ev = Evidence(
        category=EvidenceCategory.PERFORMANCE,
        severity=Severity.WARNING,
        title="Top resource consumers",
        description="High CPU usage",
        source="winfix_diagnostics",
        data={"kind": "RESOURCE_HOG_ANALYSIS", "top_resource_consumers": [{"name": "Chrome", "process_count": 1, "raw_cpu_percent": 75.0, "memory_mb": 2048.0, "impact": "HIGH", "impact_score": 8.0}]},
    )
    with patch.object(session_service.agent, "_collect_evidence", return_value=[resource_hog_ev]):
        diagnosed = await session_service.diagnose(session.session_id, DiagnoseRequest(categories=["resource_hog"]))

    # Diagnosis status is DIAGNOSED, NOT awaiting approval because no fake remediation is attached
    assert diagnosed.status == SessionStatus.DIAGNOSED
    assert len(diagnosed.diagnosis.recommended_actions) == 0
    assert len(diagnosed.execution_results) == 0
    assert len(diagnosed.verification_results) == 0


@pytest.mark.asyncio
async def test_action_specific_verification(session_service):
    """TEST 5: Successful temp cleanup verifies the cleanup action only and does not claim the original performance problem was solved."""
    session = session_service.create(CreateSessionRequest(user_problem="Clear my temp folder"))

    temp_ev = Evidence(
        category=EvidenceCategory.PERFORMANCE,
        severity=Severity.WARNING,
        title="Temporary file usage",
        description="High temporary storage usage",
        source="winfix_diagnostics",
        data={"bytes": 500 * 1024**2, "file_count": 1500},
    )
    with patch.object(session_service.agent, "_collect_evidence", return_value=[temp_ev]):
        diagnosed = await session_service.diagnose(session.session_id, DiagnoseRequest(categories=["storage"]))

    approved = session_service.approve(diagnosed.session_id, {"decisions": [{"action_id": ActionId.CLEAR_TEMP_FILES, "approved": True}]})
    executed = session_service.execute(approved.session_id)
    verified = session_service.verify(executed.session_id)

    assert len(verified.verification_results) == 1
    v_res = verified.verification_results[0]
    assert v_res.action_id == ActionId.CLEAR_TEMP_FILES
    assert v_res.status == VerificationStatus.VERIFIED
    # Summary specifically refers to temporary files / storage, not solving general resource hog
    assert "bytes reclaimed" in v_res.summary or "directory size" in v_res.summary.lower()
