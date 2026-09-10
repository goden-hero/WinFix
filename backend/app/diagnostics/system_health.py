from __future__ import annotations

import platform

from app.schemas.evidence import Evidence, EvidenceCategory, Severity


def check_system_health() -> list[Evidence]:
    """Read-only starter implementation; event/service enrichments are a Windows TODO."""
    return [
        Evidence(
            category=EvidenceCategory.SYSTEM_HEALTH,
            severity=Severity.INFO,
            title="Operating system",
            description=f"Detected {platform.system()} {platform.release()}.",
            source="platform",
            data={"system": platform.system(), "release": platform.release(), "version": platform.version()},
        )
    ]
