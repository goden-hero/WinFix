from app.diagnostics.crashes import investigate_crashes
from app.diagnostics.optimization import analyze_windows_optimization
from app.diagnostics.performance import diagnose_performance
from app.diagnostics.privacy import analyze_privacy
from app.diagnostics.system_health import check_system_health

__all__ = [
    "analyze_privacy",
    "analyze_windows_optimization",
    "check_system_health",
    "diagnose_performance",
    "investigate_crashes",
]
