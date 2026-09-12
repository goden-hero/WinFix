"""Comprehensive Pytest test suite for Windows Explorer / Taskbar Crash Recovery feature.

Tests read-only diagnostics, structured evidence, safety validation, action registration,
controlled execution, pre-execution checks, independent verification, and agent integration.
"""

import os
import platform
import pytest
from unittest.mock import patch

from app.agent.winfix_agent import DeterministicHarness, WinFixAgent
from app.diagnostics.explorer import (
    KIND_EXPLORER_DIAGNOSIS,
    TARGET_PROCESS_NAME,
    diagnose_explorer,
)
from app.executor.executor import ControlledExecutor
from app.executor.registry import ActionRegistry, registry
from app.executor.winutil_adapter import NativeWindowsAdapter
from app.safety.validator import ActionValidationError, ActionValidator
from app.schemas.actions import (
    ActionDefinition,
    ActionId,
    ApprovalDecision,
    ApprovalRequest,
    ExecutionResult,
    RecommendedAction,
    RiskLevel,
)
from app.schemas.evidence import Evidence, EvidenceCategory, Severity
from app.schemas.session import CreateSessionRequest, DiagnoseRequest
from app.schemas.verification import VerificationStatus
from app.services.session_service import SessionService
from app.storage.database import SessionStore


# --- Test Providers ---
def fake_running_explorer():
    return [{"pid": 1234, "name": "explorer.exe", "status": "running"}]


def fake_multiple_explorer():
    return [
        {"pid": 1234, "name": "explorer.exe", "status": "running"},
        {"pid": 5678, "name": "explorer.exe", "status": "running"},
    ]


def fake_absent_explorer():
    return []


def fake_missing_info_explorer():
    return [{"name": "explorer.exe"}, {"pid": None, "name": "explorer.exe"}]


def fake_malformed_explorer():
    return "not-a-list"


def fake_unrelated_process_explorer():
    return [{"pid": 9999, "name": "notepad.exe", "status": "running"}]


# --- Unit Tests ---

def test_1_windows_platform_detection():
    is_win = platform.system() == "Windows"
    ev = diagnose_explorer(proc_provider=fake_running_explorer)
    assert ev.category == EvidenceCategory.EXPLORER
    assert ev.data["kind"] == KIND_EXPLORER_DIAGNOSIS


def test_2_non_windows_provider_behavior():
    with patch("app.diagnostics.explorer.platform.system", return_value="Linux"):
        ev = diagnose_explorer(proc_provider=None)
        assert ev.data["status"] == "unsupported"
        assert ev.data["running"] is False
        assert any("unsupported" in lim.lower() or "windows" in lim.lower() for lim in ev.data["limitations"])


def test_3_explorer_process_present():
    ev = diagnose_explorer(proc_provider=fake_running_explorer)
    assert ev.data["running"] is True
    assert ev.data["process_count"] == 1
    assert ev.data["process_ids"] == [1234]
    assert ev.data["taskbar_impact"] == "none"
    assert ev.data["status"] == "healthy"
    assert ev.severity == Severity.INFO


def test_4_explorer_process_absent():
    ev = diagnose_explorer(proc_provider=fake_absent_explorer)
    assert ev.data["running"] is False
    assert ev.data["process_count"] == 0
    assert ev.data["process_ids"] == []
    assert ev.data["taskbar_impact"] == "likely_affected"
    assert ev.data["status"] == "warning"
    assert ev.severity == Severity.WARNING
    assert "Windows Explorer process is not running." in ev.data["warnings"]


def test_5_multiple_explorer_process_records():
    ev = diagnose_explorer(proc_provider=fake_multiple_explorer)
    assert ev.data["running"] is True
    assert ev.data["process_count"] == 2
    assert ev.data["process_ids"] == [1234, 5678]


def test_6_missing_process_information():
    ev = diagnose_explorer(proc_provider=fake_missing_info_explorer)
    assert ev.data["running"] is False
    assert ev.data["process_count"] == 0


def test_7_malformed_provider_data():
    ev = diagnose_explorer(proc_provider=fake_malformed_explorer)
    assert ev.data["status"] == "unavailable"
    assert "non-list data structure" in ev.data["limitations"][0]


def test_8_structured_evidence_serialization():
    ev = diagnose_explorer(proc_provider=fake_running_explorer)
    dumped = ev.model_dump(mode="json")
    assert dumped["category"] == "explorer"
    assert dumped["data"]["process_name"] == "explorer.exe"


@pytest.mark.asyncio
async def test_9_agent_routing_for_taskbar_requests():
    agent = WinFixAgent()
    prompts = [
        "My taskbar disappeared.",
        "My desktop icons are gone.",
        "Windows Explorer crashed.",
        "Restart the Windows shell.",
        "My Start menu is not working.",
        "Diagnose an Explorer crash.",
    ]
    for prompt in prompts:
        with patch.object(WinFixAgent, "_collect_evidence", return_value=[diagnose_explorer(fake_absent_explorer)]) as mock_collect:
            evidence, diagnosis = await agent.investigate(prompt, categories=[])
            assert mock_collect.called
            called_categories = mock_collect.call_args[0][0]
            assert "explorer" in called_categories


@pytest.mark.asyncio
async def test_10_finding_generated_when_explorer_is_absent():
    harness = DeterministicHarness()
    ev = diagnose_explorer(proc_provider=fake_absent_explorer)
    diag = await harness.diagnose("taskbar disappeared", [ev])
    assert any(cause.title == "Windows Explorer is not running" for cause in diag.probable_causes)
    assert any(rec.action_id == ActionId.RESTART_WINDOWS_EXPLORER for rec in diag.recommended_actions)


@pytest.mark.asyncio
async def test_11_no_false_crash_finding_when_explorer_is_present():
    harness = DeterministicHarness()
    ev = diagnose_explorer(proc_provider=fake_running_explorer)
    diag = await harness.diagnose("taskbar check", [ev])
    assert not any(cause.title == "Windows Explorer is not running" for cause in diag.probable_causes)
    assert not any(rec.action_id == ActionId.RESTART_WINDOWS_EXPLORER for rec in diag.recommended_actions)
    assert any("running" in finding.title.lower() for finding in diag.findings)


@pytest.mark.asyncio
async def test_12_no_definitive_finding_when_diagnostics_unavailable():
    harness = DeterministicHarness()
    with patch("app.diagnostics.explorer.platform.system", return_value="Linux"):
        ev = diagnose_explorer(proc_provider=None)
        diag = await harness.diagnose("taskbar check", [ev])
        assert not any(cause.title == "Windows Explorer is not running" for cause in diag.probable_causes)
        assert not any(rec.action_id == ActionId.RESTART_WINDOWS_EXPLORER for rec in diag.recommended_actions)
        assert any("unsupported" in finding.title.lower() for finding in diag.findings)


def test_13_action_id_registration():
    reg = ActionRegistry()
    definition = reg.get(ActionId.RESTART_WINDOWS_EXPLORER)
    assert definition.action_id == ActionId.RESTART_WINDOWS_EXPLORER
    assert definition.enabled is True


def test_14_fixed_action_metadata():
    definition = registry.get(ActionId.RESTART_WINDOWS_EXPLORER)
    assert definition.name == "Restart Windows Explorer"
    assert definition.risk_level == RiskLevel.MEDIUM
    assert definition.requires_approval is True
    assert definition.parameter_schema == {"type": "object", "properties": {}, "additionalProperties": False}


def test_15_approval_is_required():
    definition = registry.get(ActionId.RESTART_WINDOWS_EXPLORER)
    assert definition.requires_approval is True


def test_16_action_accepts_no_parameters():
    validator = ActionValidator(registry)
    rec = RecommendedAction(action_id=ActionId.RESTART_WINDOWS_EXPLORER, reason="Explorer down", parameters={})
    validator.validate_recommendation(rec)


def test_17_unexpected_parameters_are_rejected():
    validator = ActionValidator(registry)
    rec = RecommendedAction(action_id=ActionId.RESTART_WINDOWS_EXPLORER, reason="Explorer down", parameters={"unexpected": True})
    with pytest.raises(ActionValidationError):
        validator.validate_recommendation(rec)


def test_18_process_names_are_rejected():
    validator = ActionValidator(registry)
    rec = RecommendedAction(action_id=ActionId.RESTART_WINDOWS_EXPLORER, reason="Test", parameters={"process_name": "notepad.exe"})
    with pytest.raises(ActionValidationError):
        validator.validate_recommendation(rec)


def test_19_pids_are_rejected():
    validator = ActionValidator(registry)
    rec = RecommendedAction(action_id=ActionId.RESTART_WINDOWS_EXPLORER, reason="Test", parameters={"pid": 1234})
    with pytest.raises(ActionValidationError):
        validator.validate_recommendation(rec)


def test_20_executable_paths_are_rejected():
    validator = ActionValidator(registry)
    rec = RecommendedAction(action_id=ActionId.RESTART_WINDOWS_EXPLORER, reason="Test", parameters={"path": "C:\\other.exe"})
    with pytest.raises(ActionValidationError):
        validator.validate_recommendation(rec)


def test_21_arbitrary_arguments_are_rejected():
    validator = ActionValidator(registry)
    rec = RecommendedAction(action_id=ActionId.RESTART_WINDOWS_EXPLORER, reason="Test", parameters={"args": ["/something"]})
    with pytest.raises(ActionValidationError):
        validator.validate_recommendation(rec)


def test_22_arbitrary_shell_commands_are_rejected():
    validator = ActionValidator(registry)
    rec = RecommendedAction(action_id=ActionId.RESTART_WINDOWS_EXPLORER, reason="Test", parameters={"command": "taskkill /im explorer.exe"})
    with pytest.raises(ActionValidationError):
        validator.validate_recommendation(rec)


def test_23_non_windows_recovery_is_rejected():
    adapter = NativeWindowsAdapter(explorer_diagnoser=lambda: diagnose_explorer(fake_absent_explorer))
    with patch("platform.system", return_value="Linux"):
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": ""}):
            res = adapter.execute(ActionId.RESTART_WINDOWS_EXPLORER, {})
            assert res.status == "unsupported"


def test_24_explorer_is_rechecked_before_execution():
    called = []
    def mock_diagnoser():
        called.append(True)
        return diagnose_explorer(fake_running_explorer)

    adapter = NativeWindowsAdapter(explorer_diagnoser=mock_diagnoser)
    res = adapter.execute(ActionId.RESTART_WINDOWS_EXPLORER, {})
    assert len(called) == 1
    assert res.status == "already_running"


def test_25_explorer_is_not_launched_when_already_running():
    adapter = NativeWindowsAdapter(explorer_diagnoser=lambda: diagnose_explorer(fake_running_explorer))
    res = adapter.execute(ActionId.RESTART_WINDOWS_EXPLORER, {})
    assert res.status == "already_running"
    assert "already running" in res.message


def test_26_only_fixed_explorer_can_be_launched():
    launched = []
    def mock_launcher():
        launched.append("explorer.exe")
        return ExecutionResult(action_id=ActionId.RESTART_WINDOWS_EXPLORER, status="success", message="OK", details={"target_process": "explorer.exe"})

    adapter = NativeWindowsAdapter(
        explorer_diagnoser=lambda: diagnose_explorer(fake_absent_explorer),
        explorer_launcher=mock_launcher,
    )
    res = adapter.execute(ActionId.RESTART_WINDOWS_EXPLORER, {})
    assert res.status == "success"
    assert launched == ["explorer.exe"]


def test_27_no_unrelated_process_can_be_terminated_or_launched():
    adapter = NativeWindowsAdapter(explorer_diagnoser=lambda: diagnose_explorer(fake_absent_explorer))
    rec = RecommendedAction(action_id=ActionId.RESTART_WINDOWS_EXPLORER, reason="Explorer down", parameters={"target": "notepad.exe"})
    validator = ActionValidator(registry)
    with pytest.raises(ActionValidationError):
        validator.validate_recommendation(rec)


def test_28_execution_failure_is_reported():
    def mock_failing_launcher():
        raise OSError("Permission denied")

    adapter = NativeWindowsAdapter(
        explorer_diagnoser=lambda: diagnose_explorer(fake_absent_explorer),
        explorer_launcher=mock_failing_launcher,
    )
    res = adapter.execute(ActionId.RESTART_WINDOWS_EXPLORER, {})
    assert res.status == "failed"
    assert "Permission denied" in res.message


@pytest.mark.asyncio
async def test_29_independent_verification_is_performed():
    store = SessionStore()
    service = SessionService(store=store)
    session = service.create(CreateSessionRequest(user_problem="My taskbar disappeared."))
    
    absent_ev = diagnose_explorer(fake_absent_explorer)
    diag_res = await DeterministicHarness().diagnose("taskbar", [absent_ev])
    
    async def mock_investigate(user_problem, categories):
        return [absent_ev], diag_res
    
    with patch.object(WinFixAgent, "investigate", side_effect=mock_investigate):
        session = await service.diagnose(session.session_id, DiagnoseRequest(categories=["explorer"]))
    
    session = service.approve(session.session_id, ApprovalRequest(decisions=[ApprovalDecision(action_id=ActionId.RESTART_WINDOWS_EXPLORER, approved=True)]))
    
    with patch.object(NativeWindowsAdapter, "execute", return_value=ExecutionResult(action_id=ActionId.RESTART_WINDOWS_EXPLORER, status="success", message="Launched explorer.exe")):
        session = service.execute(session.session_id)
    
    with patch("app.services.session_service.diagnose_explorer", return_value=diagnose_explorer(fake_running_explorer)):
        session = service.verify(session.session_id)
        assert len(session.verification_results) == 1
        ver = session.verification_results[0]
        assert ver.status == VerificationStatus.VERIFIED
        assert "Windows Explorer (explorer.exe) is running" in ver.summary


@pytest.mark.asyncio
async def test_30_verification_failure_is_reported():
    store = SessionStore()
    service = SessionService(store=store)
    session = service.create(CreateSessionRequest(user_problem="My taskbar disappeared."))
    absent_ev = diagnose_explorer(fake_absent_explorer)
    diag_res = await DeterministicHarness().diagnose("taskbar", [absent_ev])
    
    async def mock_investigate(user_problem, categories):
        return [absent_ev], diag_res
    
    with patch.object(WinFixAgent, "investigate", side_effect=mock_investigate):
        session = await service.diagnose(session.session_id, DiagnoseRequest(categories=["explorer"]))
    
    session = service.approve(session.session_id, ApprovalRequest(decisions=[ApprovalDecision(action_id=ActionId.RESTART_WINDOWS_EXPLORER, approved=True)]))
    
    with patch.object(NativeWindowsAdapter, "execute", return_value=ExecutionResult(action_id=ActionId.RESTART_WINDOWS_EXPLORER, status="success", message="Launched explorer.exe")):
        session = service.execute(session.session_id)
    
    with patch("app.services.session_service.diagnose_explorer", return_value=diagnose_explorer(fake_absent_explorer)):
        session = service.verify(session.session_id)
        ver = session.verification_results[0]
        assert ver.status == VerificationStatus.FAILED
        assert "still not running" in ver.summary
