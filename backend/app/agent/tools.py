"""Named high-level tool functions exposed to a future Pi adapter."""

from app.diagnostics import (
    analyze_privacy,
    analyze_windows_optimization,
    check_system_health,
    diagnose_performance,
    investigate_crashes,
)

AGENT_TOOLS = {
    "diagnose_performance": diagnose_performance,
    "check_system_health": check_system_health,
    "investigate_crashes": investigate_crashes,
    "analyze_windows_optimization": analyze_windows_optimization,
    "analyze_privacy": analyze_privacy,
}
