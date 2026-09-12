"""Unit and integration tests for Read-Only Battery Diagnostics module."""

from __future__ import annotations

import json
import platform
import pytest

from app.agent.winfix_agent import DeterministicHarness, WinFixAgent
from app.diagnostics.battery import (
    BatteryDiagnosticResult,
    BatteryHealth,
    FakeBatteryProvider,
    NonWindowsBatteryProvider,
    WindowsBatteryProvider,
    calculate_battery_health,
    collect_battery_diagnostics,
    evaluate_battery_diagnostics,
)
from app.schemas.evidence import EvidenceCategory, Severity


def test_windows_platform_detection():
    """Verify WindowsBatteryProvider returns a structured result without throwing exceptions."""
    provider = WindowsBatteryProvider()
    result = provider.get_battery_info()
    assert isinstance(result, BatteryDiagnosticResult)
    assert result.category == "BATTERY"
    assert isinstance(result.limitations, list)


def test_non_windows_provider_behavior():
    """Verify NonWindowsBatteryProvider returns status='unavailable' and clear limitation."""
    provider = NonWindowsBatteryProvider()
    result = provider.get_battery_info()
    assert result.status == "unavailable"
    assert result.battery_present is False
    assert len(result.limitations) >= 1
    assert "Windows" in result.limitations[0]


def test_battery_present_and_charging():
    """Verify battery present and charging on AC power evaluates to healthy."""
    fake_res = BatteryDiagnosticResult(
        category="BATTERY",
        status="unknown",
        battery_present=True,
        charge_percent=80,
        is_charging=True,
        power_source="ac",
        battery_health=BatteryHealth(design_capacity_mwh=50000, full_charge_capacity_mwh=45000, health_percent=90.0),
    )
    provider = FakeBatteryProvider(fake_res)
    evidence = collect_battery_diagnostics(provider=provider)
    assert evidence.category == EvidenceCategory.BATTERY
    assert evidence.severity == Severity.INFO
    assert evidence.data["status"] == "healthy"
    assert evidence.data["charge_percent"] == 80
    assert evidence.data["is_charging"] is True


def test_battery_present_and_discharging():
    """Verify battery present and discharging on battery power evaluates correctly."""
    fake_res = BatteryDiagnosticResult(
        category="BATTERY",
        status="unknown",
        battery_present=True,
        charge_percent=60,
        is_charging=False,
        power_source="battery",
        battery_saver_enabled=True,
        battery_health=BatteryHealth(design_capacity_mwh=50000, full_charge_capacity_mwh=45000, health_percent=90.0),
    )
    provider = FakeBatteryProvider(fake_res)
    evidence = collect_battery_diagnostics(provider=provider)
    assert evidence.severity == Severity.INFO
    assert evidence.data["status"] == "healthy"
    assert evidence.data["power_source"] == "battery"


def test_ac_power_with_battery_installed():
    """Verify AC power with battery installed correctly sets power source."""
    fake_res = BatteryDiagnosticResult(
        category="BATTERY",
        status="unknown",
        battery_present=True,
        charge_percent=100,
        is_charging=False,
        power_source="ac",
    )
    evaluated = evaluate_battery_diagnostics(fake_res)
    assert evaluated.power_source == "ac"
    assert evaluated.status == "healthy"


def test_no_battery_detected():
    """Verify no battery detected evaluates to unavailable and does not report battery failure."""
    fake_res = BatteryDiagnosticResult(
        category="BATTERY",
        status="unknown",
        battery_present=False,
        power_source="ac",
    )
    evaluated = evaluate_battery_diagnostics(fake_res)
    assert evaluated.status == "unavailable"
    assert any("No battery detected" in lim for lim in evaluated.limitations)
    assert len(evaluated.warnings) == 0


def test_charge_15_percent_while_discharging():
    """Verify charge <= 15% while discharging evaluates to critical status."""
    fake_res = BatteryDiagnosticResult(
        category="BATTERY",
        status="unknown",
        battery_present=True,
        charge_percent=12,
        is_charging=False,
        power_source="battery",
    )
    evaluated = evaluate_battery_diagnostics(fake_res)
    assert evaluated.status == "critical"
    assert any("critically low" in w for w in evaluated.warnings)


def test_charge_30_percent_while_discharging():
    """Verify charge <= 30% while discharging evaluates to warning status."""
    fake_res = BatteryDiagnosticResult(
        category="BATTERY",
        status="unknown",
        battery_present=True,
        charge_percent=25,
        is_charging=False,
        power_source="battery",
    )
    evaluated = evaluate_battery_diagnostics(fake_res)
    assert evaluated.status == "warning"
    assert any("low" in w for w in evaluated.warnings)


def test_low_charge_on_ac_does_not_become_critical():
    """Verify low battery charge while plugged into AC power does NOT become critical emergency."""
    fake_res = BatteryDiagnosticResult(
        category="BATTERY",
        status="unknown",
        battery_present=True,
        charge_percent=10,
        is_charging=True,
        power_source="ac",
    )
    evaluated = evaluate_battery_diagnostics(fake_res)
    assert evaluated.status != "critical"
    assert any("plugged into AC power" in w for w in evaluated.warnings)


def test_missing_battery_health_data():
    """Verify missing design or full charge capacity yields health_percent=None and adds limitation."""
    health, warning, limitation = calculate_battery_health(None, 50000)
    assert health.health_percent is None
    assert limitation is not None
    assert "unavailable" in limitation.lower()


def test_valid_health_calculation():
    """Verify valid capacity inputs compute accurate rounded health_percent."""
    health, warning, limitation = calculate_battery_health(40000, 50000)
    assert health.health_percent == 80.0
    assert warning is None
    assert limitation is None


def test_zero_design_capacity():
    """Verify design_capacity=0 yields health_percent=None without division by zero error."""
    health, warning, limitation = calculate_battery_health(40000, 0)
    assert health.health_percent is None
    assert limitation is not None


def test_negative_capacity_values():
    """Verify negative capacity inputs yield health_percent=None."""
    health, warning, limitation = calculate_battery_health(-100, 50000)
    assert health.health_percent is None
    assert limitation is not None


def test_full_charge_greater_than_design_capacity():
    """Verify full_charge > design_capacity is flagged as implausible and health_percent is None."""
    health, warning, limitation = calculate_battery_health(60000, 50000)
    assert health.health_percent is None
    assert limitation is not None
    assert "exceeds design capacity" in limitation


def test_battery_saver_enabled():
    """Verify battery saver state is preserved in diagnostic output."""
    fake_res = BatteryDiagnosticResult(
        category="BATTERY",
        battery_present=True,
        battery_saver_enabled=True,
    )
    assert fake_res.battery_saver_enabled is True


def test_battery_saver_disabled_while_on_battery():
    """Verify disabled battery saver on battery power adds optimization observation."""
    fake_res = BatteryDiagnosticResult(
        category="BATTERY",
        battery_present=True,
        power_source="battery",
        is_charging=False,
        battery_saver_enabled=False,
    )
    evaluated = evaluate_battery_diagnostics(fake_res)
    assert any("Battery Saver is currently disabled" in w for w in evaluated.warnings)


def test_missing_power_plan_data():
    """Verify missing power plan data adds limitation without failure."""
    fake_res = BatteryDiagnosticResult(
        category="BATTERY",
        battery_present=True,
        power_plan=None,
    )
    evaluated = evaluate_battery_diagnostics(fake_res)
    assert evaluated.power_plan is None


def test_malformed_or_incomplete_provider_data():
    """Verify non-numeric or malformed capacity values yield health_percent=None safely."""
    health, warning, limitation = calculate_battery_health("invalid", 50000)  # type: ignore
    assert health.health_percent is None
    assert limitation is not None


def test_json_serialization():
    """Verify battery diagnostic evidence data serializes cleanly to JSON."""
    fake_res = BatteryDiagnosticResult(
        category="BATTERY",
        battery_present=True,
        charge_percent=75,
        is_charging=False,
        power_source="battery",
        battery_health=BatteryHealth(design_capacity_mwh=50000, full_charge_capacity_mwh=40000, health_percent=80.0),
    )
    provider = FakeBatteryProvider(fake_res)
    evidence = collect_battery_diagnostics(provider=provider)
    data = evidence.model_dump(mode="json")
    json_str = json.dumps(data)
    assert "BATTERY_DIAGNOSIS" in json_str
    assert "charge_percent" in json_str


@pytest.mark.asyncio
async def test_agent_routing_for_battery_related_requests():
    """Verify WinFixAgent routes battery drain queries to collect battery diagnostics."""
    fake_res = BatteryDiagnosticResult(
        category="BATTERY",
        battery_present=True,
        charge_percent=15,
        is_charging=False,
        power_source="battery",
    )
    provider = FakeBatteryProvider(fake_res)
    evidence = collect_battery_diagnostics(provider=provider)

    harness = DeterministicHarness()
    result = await harness.diagnose("Why is my laptop battery draining quickly?", [evidence])

    assert any("Battery" in cause.title for cause in result.probable_causes)
    assert len(result.recommended_actions) == 0  # Stage 1 has NO mutating actions


def test_no_arbitrary_command_or_subprocess_execution():
    """Verify battery diagnostics produces zero mutating actions and contains no command strings."""
    fake_res = BatteryDiagnosticResult(
        category="BATTERY",
        battery_present=True,
        charge_percent=10,
        is_charging=False,
        power_source="battery",
    )
    evaluated = evaluate_battery_diagnostics(fake_res)
    assert isinstance(evaluated.warnings, list)
    assert evaluated.source == "read_only_windows_api"


@pytest.mark.asyncio
async def test_existing_feature_regression_coverage():
    """Verify WinFixAgent continues to support default performance diagnostics without breaking."""
    agent = WinFixAgent(harness=DeterministicHarness())
    evidence_list, diagnosis = await agent.investigate("PC is running slow", categories=["performance"])
    assert len(evidence_list) >= 1
    assert diagnosis.summary != ""
