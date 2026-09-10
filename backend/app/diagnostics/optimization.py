from app.diagnostics.performance import diagnose_performance
from app.schemas.evidence import Evidence, EvidenceCategory


def analyze_windows_optimization() -> list[Evidence]:
    """Reuses bounded startup/temp evidence until optional-app analysis is implemented."""
    return [
        item for item in diagnose_performance() if item.category in {EvidenceCategory.PERFORMANCE, EvidenceCategory.OPTIMIZATION}
    ]
