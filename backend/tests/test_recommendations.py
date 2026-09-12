"""Tests for recommendation generation in WinFixAgent DeterministicHarness."""

from __future__ import annotations

import pytest

from app.agent.winfix_agent import DeterministicHarness
from app.schemas.actions import ActionId
from app.schemas.evidence import Evidence, EvidenceCategory, Severity


@pytest.mark.asyncio
async def test_startup_warning_generates_recommendation():
    """Verify non-demo active startup apps generate a DISABLE_STARTUP_APP recommendation."""
    startup_evidence = Evidence(
        category=EvidenceCategory.PERFORMANCE,
        severity=Severity.WARNING,
        title="Startup applications",
        description="Found 3 active startup applications in HKCU Run.",
        source="Windows Registry HKCU Run",
        data={
            "count": 3,
            "enabled_count": 3,
            "entries": [
                {"id": "hkcu_run:SomeApp", "name": "SomeApp", "enabled": True, "is_demo": False},
                {"id": "hkcu_run:OtherApp", "name": "OtherApp", "enabled": True, "is_demo": False},
            ],
        },
    )

    harness = DeterministicHarness()
    result = await harness.diagnose("PC is slow", [startup_evidence])

    assert len(result.recommended_actions) >= 1
    action = result.recommended_actions[0]
    assert action.action_id == ActionId.DISABLE_STARTUP_APP
    assert action.parameters.get("startup_entry_id") == "hkcu_run:SomeApp"


@pytest.mark.asyncio
async def test_windows_update_critical_generates_dism_sfc_recommendation():
    """Verify Windows Update or core service critical/warning evidence generates DISM/SFC recommendations."""
    wu_evidence = Evidence(
        category=EvidenceCategory.SYSTEM_HEALTH,
        severity=Severity.CRITICAL,
        title="Windows Update core services",
        description="Windows Update service state is stopped or degraded.",
        source="wuauserv",
        data={"service": "wuauserv", "status": "stopped"},
    )

    harness = DeterministicHarness()
    result = await harness.diagnose("Windows update broken", [wu_evidence])

    assert len(result.recommended_actions) >= 1
    action_ids = [a.action_id for a in result.recommended_actions]
    assert ActionId.RUN_DISM_HEALTH_CHECK in action_ids or ActionId.RUN_SFC_SCAN in action_ids
