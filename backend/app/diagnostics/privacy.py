from app.schemas.evidence import Evidence, EvidenceCategory, Severity


def analyze_privacy() -> list[Evidence]:
    """Contract placeholder. Future reads must map only to supported privacy profiles."""
    return [
        Evidence(
            category=EvidenceCategory.PRIVACY,
            severity=Severity.INFO,
            title="Privacy analysis pending Windows implementation",
            description="Only selected settings represented by action profiles will be analyzed.",
            source="winfix diagnostic scaffold",
            data={"implemented": False},
        )
    ]
