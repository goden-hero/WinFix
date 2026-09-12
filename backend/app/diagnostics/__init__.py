from app.diagnostics.battery import collect_battery_diagnostics
from app.diagnostics.crashes import investigate_crashes
from app.diagnostics.optimization import analyze_windows_optimization
from app.diagnostics.performance import diagnose_performance
from app.diagnostics.privacy import analyze_privacy
from app.diagnostics.resource_hog import detect_resource_hogs
from app.diagnostics.system_health import check_system_health
from app.diagnostics.windows_update import diagnose_windows_update

__all__ = [
    "analyze_privacy",
    "analyze_windows_optimization",
    "check_system_health",
    "collect_battery_diagnostics",
    "detect_resource_hogs",
    "diagnose_performance",
    "diagnose_windows_update",
    "investigate_crashes",
]

