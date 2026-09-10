from app.schemas.actions import RiskLevel


class SafetyPolicy:
    """Deterministic policy. Agent output never changes these rules."""

    @staticmethod
    def may_execute(risk_level: RiskLevel, approved: bool) -> bool:
        if risk_level is RiskLevel.HIGH:
            return False
        if risk_level is RiskLevel.MEDIUM:
            return approved
        return True

    @staticmethod
    def approval_required(risk_level: RiskLevel) -> bool:
        return risk_level is not RiskLevel.LOW
