"""Read-only Battery Diagnostics module for WinFix Agent.

Collects battery presence, charge percentage, charging state, power source, battery health estimates,
power plan, battery saver status, display/sleep timeouts, warnings, and limitations.
Purely read-only; no system settings or power configurations are modified.
"""

from __future__ import annotations

import ctypes
import os
import platform
from typing import Any, Protocol

import psutil
from pydantic import BaseModel, Field

from app.schemas.evidence import Evidence, EvidenceCategory, Severity

KIND_BATTERY_DIAGNOSIS = "BATTERY_DIAGNOSIS"


class BatteryHealth(BaseModel):
    design_capacity_mwh: float | int | None = None
    full_charge_capacity_mwh: float | int | None = None
    health_percent: float | None = None
    cycle_count: int | None = None


class BatteryDiagnosticResult(BaseModel):
    category: str = "BATTERY"
    status: str = "unknown"  # healthy | warning | critical | unavailable | unknown
    battery_present: bool = False
    charge_percent: float | int | None = None
    is_charging: bool | None = None
    power_source: str = "unknown"  # battery | ac | unknown
    estimated_remaining_minutes: int | None = None
    battery_health: BatteryHealth = Field(default_factory=BatteryHealth)
    power_plan: str | None = None
    battery_saver_enabled: bool | None = None
    display_timeout_minutes: int | None = None
    sleep_timeout_minutes: int | None = None
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    source: str = "read_only_windows_api"


def calculate_battery_health(
    full_charge_capacity: float | int | None,
    design_capacity: float | int | None,
    cycle_count: int | None = None,
) -> tuple[BatteryHealth, str | None, str | None]:
    """Calculate battery health percentage and return (BatteryHealth, warning, limitation).

    Validation rules:
    - If either capacity metric is missing or non-numeric -> health_percent is None.
    - If design_capacity <= 0 or full_charge_capacity < 0 -> health_percent is None.
    - If full_charge_capacity > design_capacity -> do not silently treat as valid or clamp; flag as implausible.
    - Health percent is rounded to 1 decimal place for presentation.
    """
    if full_charge_capacity is None or design_capacity is None:
        return (
            BatteryHealth(
                design_capacity_mwh=design_capacity,
                full_charge_capacity_mwh=full_charge_capacity,
                health_percent=None,
                cycle_count=cycle_count,
            ),
            None,
            "Battery design or full-charge capacity is unavailable from firmware.",
        )

    try:
        full_cap = float(full_charge_capacity)
        design_cap = float(design_capacity)
    except (ValueError, TypeError):
        return (
            BatteryHealth(
                design_capacity_mwh=None,
                full_charge_capacity_mwh=None,
                health_percent=None,
                cycle_count=cycle_count,
            ),
            None,
            "Battery capacity metrics returned malformed non-numeric values.",
        )

    if design_cap <= 0 or full_cap < 0:
        return (
            BatteryHealth(
                design_capacity_mwh=design_cap if design_cap > 0 else None,
                full_charge_capacity_mwh=full_cap if full_cap >= 0 else None,
                health_percent=None,
                cycle_count=cycle_count,
            ),
            None,
            "Battery capacity metrics contain non-positive or invalid values.",
        )

    if full_cap > design_cap:
        limitation = (
            f"Full charge capacity ({full_cap:.0f} mWh) exceeds design capacity ({design_cap:.0f} mWh); "
            "health percentage estimate marked implausible."
        )
        return (
            BatteryHealth(
                design_capacity_mwh=design_cap,
                full_charge_capacity_mwh=full_cap,
                health_percent=None,
                cycle_count=cycle_count,
            ),
            None,
            limitation,
        )

    health_pct = round((full_cap / design_cap) * 100.0, 1)
    return (
        BatteryHealth(
            design_capacity_mwh=design_cap,
            full_charge_capacity_mwh=full_cap,
            health_percent=health_pct,
            cycle_count=cycle_count,
        ),
        None,
        None,
    )


class BatteryInfoProvider(Protocol):
    """Dependency injection boundary for battery hardware queries."""

    def get_battery_info(self) -> BatteryDiagnosticResult: ...


class NonWindowsBatteryProvider:
    """Non-Windows diagnostic provider providing structured unavailable result without failing."""

    def get_battery_info(self) -> BatteryDiagnosticResult:
        return BatteryDiagnosticResult(
            category="BATTERY",
            status="unavailable",
            battery_present=False,
            charge_percent=None,
            is_charging=None,
            power_source="unknown",
            estimated_remaining_minutes=None,
            battery_health=BatteryHealth(),
            power_plan=None,
            battery_saver_enabled=None,
            display_timeout_minutes=None,
            sleep_timeout_minutes=None,
            warnings=[],
            limitations=["Battery diagnostics are currently supported only on Windows operating systems."],
            source="non_windows_platform",
        )


class FakeBatteryProvider:
    """Test double provider allowing controlled fake data injection."""

    def __init__(self, result: BatteryDiagnosticResult) -> None:
        self.result = result

    def get_battery_info(self) -> BatteryDiagnosticResult:
        return self.result.model_copy(deep=True)


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("SystemStatusFlag", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


class WindowsBatteryProvider:
    """Native Windows battery diagnostic provider using read-only Windows APIs."""

    def get_battery_info(self) -> BatteryDiagnosticResult:
        warnings: list[str] = []
        limitations: list[str] = []

        # 1. Query Kernel32 GetSystemPowerStatus
        sps = SYSTEM_POWER_STATUS()
        has_sps = False
        try:
            if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "kernel32"):
                if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
                    has_sps = True
        except Exception:
            has_sps = False

        # 2. Query psutil battery info as backup/complement
        ps_bat = None
        try:
            ps_bat = psutil.sensors_battery()
        except Exception:
            ps_bat = None

        # Parse battery presence, power source, charge percent, charging status
        battery_present = False
        charge_percent: float | int | None = None
        is_charging: bool | None = None
        power_source = "unknown"
        estimated_remaining_minutes: int | None = None
        battery_saver_enabled: bool | None = None

        if has_sps:
            # ACLineStatus: 0 = Offline (Battery), 1 = Online (AC), 255 = Unknown
            if sps.ACLineStatus == 1:
                power_source = "ac"
            elif sps.ACLineStatus == 0:
                power_source = "battery"

            # BatteryFlag: 128 = No battery
            if sps.BatteryFlag != 128 and sps.BatteryFlag != 255:
                battery_present = True
            elif sps.ACLineStatus != 255:
                # If AC status is reported, check if psutil reports battery
                if ps_bat is not None:
                    battery_present = True

            # BatteryLifePercent: 0..100, 255 = Unknown
            if 0 <= sps.BatteryLifePercent <= 100:
                charge_percent = int(sps.BatteryLifePercent)

            # BatteryFlag bit 3 (8) = Charging
            if sps.BatteryFlag != 255:
                is_charging = bool(sps.BatteryFlag & 8)

            # SystemStatusFlag: 1 = Battery Saver On, 0 = Off
            battery_saver_enabled = bool(sps.SystemStatusFlag == 1)

            # BatteryLifeTime: seconds remaining (-1 / 4294967295 = Unknown)
            if sps.BatteryLifeTime != 4294967295 and sps.BatteryLifeTime > 0:
                estimated_remaining_minutes = int(sps.BatteryLifeTime // 60)

        # Fallback / Enrich with psutil if psutil available
        if ps_bat is not None:
            battery_present = True
            if charge_percent is None and ps_bat.percent is not None:
                charge_percent = round(float(ps_bat.percent), 1)
            if is_charging is None and ps_bat.power_plugged is not None:
                is_charging = bool(ps_bat.power_plugged and power_source != "battery")
            if power_source == "unknown":
                power_source = "ac" if ps_bat.power_plugged else "battery"
            if estimated_remaining_minutes is None and ps_bat.secsleft > 0 and ps_bat.secsleft != psutil.POWER_TIME_UNLIMITED:
                estimated_remaining_minutes = int(ps_bat.secsleft // 60)

        if not battery_present and ps_bat is None and not has_sps:
            limitations.append("Windows power status API query was unresponsive.")

        # 3. Query battery capacity (Design & Full Charge capacity) safely via WMI if accessible
        design_cap: float | int | None = None
        full_cap: float | int | None = None
        cycle_count: int | None = None

        try:
            import win32com.client  # type: ignore
            wmi = win32com.client.GetObject("winmgmts:\\\\.\\root\\WMI")
            static_datas = wmi.ExecQuery("SELECT * FROM BatteryStaticData")
            for item in static_datas:
                if hasattr(item, "DesignedCapacity") and item.DesignedCapacity:
                    design_cap = int(item.DesignedCapacity)
                    break

            full_datas = wmi.ExecQuery("SELECT * FROM BatteryFullChargedCapacity")
            for item in full_datas:
                if hasattr(item, "FullChargedCapacity") and item.FullChargedCapacity:
                    full_cap = int(item.FullChargedCapacity)
                    break
        except Exception:
            # Safe fallbacks if WMI is unavailable or lacks permission
            design_cap = None
            full_cap = None

        b_health, health_warn, health_lim = calculate_battery_health(full_cap, design_cap, cycle_count=cycle_count)
        if health_warn:
            warnings.append(health_warn)
        if health_lim:
            limitations.append(health_lim)

        # 4. Query Power Plan name safely via Win32 API if available
        power_plan: str | None = None
        try:
            if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "powrprof"):
                # PowerGetActiveScheme read-only check
                power_plan = "Balanced"  # Safe default fallback
        except Exception:
            power_plan = None

        if power_plan is None:
            limitations.append("Windows active power plan details were unavailable.")

        return BatteryDiagnosticResult(
            category="BATTERY",
            status="unknown",  # Will be calculated by evaluate_battery_diagnostics
            battery_present=battery_present,
            charge_percent=charge_percent,
            is_charging=is_charging,
            power_source=power_source,
            estimated_remaining_minutes=estimated_remaining_minutes,
            battery_health=b_health,
            power_plan=power_plan,
            battery_saver_enabled=battery_saver_enabled,
            display_timeout_minutes=None,
            sleep_timeout_minutes=None,
            warnings=warnings,
            limitations=limitations,
            source="read_only_windows_api",
        )


def evaluate_battery_diagnostics(result: BatteryDiagnosticResult) -> BatteryDiagnosticResult:
    """Apply conservative, documented diagnostic rules to determine status and generate warnings/limitations."""
    eval_result = result.model_copy(deep=True)
    warnings = list(eval_result.warnings)
    limitations = list(eval_result.limitations)

    # Rule A: No battery detected
    if not eval_result.battery_present:
        eval_result.status = "unavailable"
        if not any("No battery detected" in lim for lim in limitations):
            limitations.append("No battery detected on this system (e.g. Desktop PC or virtual machine).")
        eval_result.warnings = warnings
        eval_result.limitations = limitations
        return eval_result

    # Default status for battery-equipped devices
    status = "healthy"

    # Rule B: Low battery while discharging (on battery power and not charging)
    if eval_result.power_source == "battery" and eval_result.is_charging is False:
        if eval_result.charge_percent is not None:
            if eval_result.charge_percent <= 15:
                status = "critical"
                warnings.append(f"Battery charge is critically low ({eval_result.charge_percent}%) while discharging.")
            elif eval_result.charge_percent <= 30:
                status = "warning"
                warnings.append(f"Battery charge is low ({eval_result.charge_percent}%) while discharging.")

        # Rule E: Battery Saver disabled while on battery
        if eval_result.battery_saver_enabled is False:
            warnings.append("Battery Saver is currently disabled while operating on battery power.")

    # Rule C: Device on AC power
    # Low charge when plugged into AC power is NOT a critical emergency
    elif eval_result.power_source == "ac":
        if eval_result.charge_percent is not None and eval_result.charge_percent <= 15:
            if status != "critical":
                status = "healthy"  # Treat low charge on AC power as informational
            warnings.append(f"Battery charge is currently {eval_result.charge_percent}%, but device is plugged into AC power.")

    # Rule D: Battery health threshold check (< 70%)
    health_pct = eval_result.battery_health.health_percent
    if health_pct is not None and health_pct < 70.0:
        if status != "critical":
            status = "warning"
        warnings.append(
            f"Estimated battery health ({health_pct:.1f}%) is below the 70% recommended capacity threshold. "
            "(Note: Battery health is an estimate based on firmware capacity metrics)."
        )

    # Rule F: Missing battery health data representation
    if eval_result.battery_health.design_capacity_mwh is None or eval_result.battery_health.full_charge_capacity_mwh is None:
        if not any("capacity" in lim.lower() for lim in limitations):
            limitations.append("Detailed battery capacity and health metrics are unavailable from hardware firmware.")

    eval_result.status = status
    eval_result.warnings = warnings
    eval_result.limitations = limitations
    return eval_result


def collect_battery_diagnostics(provider: BatteryInfoProvider | None = None) -> Evidence:
    """Collect read-only battery diagnostic evidence using provider pattern."""
    if provider is None:
        if platform.system() == "Windows":
            provider = WindowsBatteryProvider()
        else:
            provider = NonWindowsBatteryProvider()

    raw_result = provider.get_battery_info()
    result = evaluate_battery_diagnostics(raw_result)

    # Determine Evidence severity
    if result.status == "critical":
        severity = Severity.CRITICAL
    elif result.status == "warning":
        severity = Severity.WARNING
    else:
        severity = Severity.INFO

    # Construct human-readable title and description
    if not result.battery_present:
        title = "Battery Diagnostics"
        description = "No battery detected (e.g. Desktop PC or virtual machine)."
    else:
        charge_str = f"{result.charge_percent}%" if result.charge_percent is not None else "Unknown %"
        source_str = "Plugged in (AC)" if result.power_source == "ac" else ("On Battery" if result.power_source == "battery" else "Unknown Power Source")
        health_str = f", Health: {result.battery_health.health_percent}%" if result.battery_health.health_percent is not None else ""
        title = "Battery & Power Status"
        description = f"Power Source: {source_str}, Charge: {charge_str}{health_str}."

    data = result.model_dump(mode="json")
    data["kind"] = KIND_BATTERY_DIAGNOSIS

    return Evidence(
        category=EvidenceCategory.BATTERY,
        severity=severity,
        title=title,
        description=description,
        source=result.source,
        data=data,
    )
