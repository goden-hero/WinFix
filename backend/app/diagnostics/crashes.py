from app.schemas.evidence import Evidence, EvidenceCategory, Severity


def investigate_crashes() -> list[Evidence]:
    """Contract placeholder: Windows Event Log collection is intentionally isolated here."""
    return [
        Evidence(
            category=EvidenceCategory.CRASH,
            severity=Severity.INFO,
            title="Crash investigation not yet expanded",
            description="Event Log parsing is planned; minidump analysis is out of scope for the MVP.",
            source="winfix diagnostic scaffold",
            data={"implemented": False},
        )
    ]
