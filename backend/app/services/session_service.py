from __future__ import annotations

from datetime import datetime, timezone

from app.agent.winfix_agent import WinFixAgent
from app.executor.executor import ControlledExecutor
from app.executor.registry import ActionRegistry, registry
from app.safety.validator import ActionValidator
from app.executor.temp_cleaner import measure_temp_dir
from app.schemas.actions import ActionId, ApprovalRequest
from app.schemas.session import CreateSessionRequest, DiagnoseRequest, SessionStatus, WinFixSession
from app.schemas.verification import VerificationMetric, VerificationResult, VerificationStatus
from app.storage.database import SessionStore


class SessionNotFoundError(KeyError):
    pass


class InvalidSessionStateError(ValueError):
    pass


class SessionService:
    def __init__(self, store: SessionStore | None = None, agent: WinFixAgent | None = None, action_registry: ActionRegistry = registry) -> None:
        self.store = store or SessionStore()
        self.agent = agent or WinFixAgent()
        self.registry = action_registry
        self.validator = ActionValidator(action_registry)
        self.executor = ControlledExecutor(action_registry)

    def _save(self, session: WinFixSession) -> WinFixSession:
        return self.store.save(session.model_copy(update={"updated_at": datetime.now(timezone.utc)}))

    def create(self, request: CreateSessionRequest) -> WinFixSession:
        return self._save(WinFixSession(user_problem=request.user_problem))

    def get(self, session_id: str) -> WinFixSession:
        session = self.store.get(session_id)
        if not session:
            raise SessionNotFoundError(session_id)
        return session

    async def diagnose(self, session_id: str, request: DiagnoseRequest) -> WinFixSession:
        session = self.get(session_id)
        if session.status not in {SessionStatus.CREATED, SessionStatus.DIAGNOSED}:
            raise InvalidSessionStateError(f"cannot diagnose a session in {session.status.value}")
        self._save(session.model_copy(update={"status": SessionStatus.DIAGNOSING}))
        evidence, diagnosis = await self.agent.investigate(session.user_problem, request.categories)
        status = SessionStatus.AWAITING_APPROVAL if diagnosis.recommended_actions else SessionStatus.DIAGNOSED
        return self._save(session.model_copy(update={"evidence": evidence, "diagnosis": diagnosis, "status": status}))

    def approve(self, session_id: str, request: ApprovalRequest) -> WinFixSession:
        session = self.get(session_id)
        if session.status not in {SessionStatus.AWAITING_APPROVAL, SessionStatus.DIAGNOSED} or not session.diagnosis:
            raise InvalidSessionStateError("a diagnosis with recommendations is required before approval")
        recommended = {item.action_id: item for item in session.diagnosis.recommended_actions}
        approvals = dict(session.approvals)
        for decision in request.decisions:
            recommendation = recommended.get(decision.action_id)
            if not recommendation:
                raise ValueError(f"{decision.action_id.value} was not recommended for this session")
            self.validator.validate_recommendation(recommendation)
            approvals[decision.action_id] = decision.approved
        return self._save(session.model_copy(update={"approvals": approvals, "status": SessionStatus.APPROVED}))

    def execute(self, session_id: str) -> WinFixSession:
        session = self.get(session_id)
        if session.status is not SessionStatus.APPROVED or not session.diagnosis:
            raise InvalidSessionStateError("approved actions are required before execution")
        results = []
        for recommendation in session.diagnosis.recommended_actions:
            if session.approvals.get(recommendation.action_id) is True:
                results.append(self.executor.execute(recommendation, approved=True))
        return self._save(session.model_copy(update={"execution_results": results, "status": SessionStatus.VERIFYING}))

    def verify(self, session_id: str) -> WinFixSession:
        session = self.get(session_id)
        if not session.execution_results:
            raise InvalidSessionStateError("no execution results are available to verify")
        
        verification_results = []
        for result in session.execution_results:
            if result.action_id == ActionId.CLEAR_TEMP_FILES:
                bytes_before = int(result.details.get("bytes_before", 0))
                files_before = int(result.details.get("file_count_before", 0))

                # Independent, fresh filesystem inspection
                now_bytes, now_files = measure_temp_dir()

                reclaimed_bytes = max(0, bytes_before - now_bytes)
                reclaimed_files = max(0, files_before - now_files)

                is_improved = now_bytes < bytes_before or (bytes_before == 0 and now_bytes == 0)
                verification_status = VerificationStatus.VERIFIED if is_improved else VerificationStatus.FAILED

                verification_results.append(
                    VerificationResult(
                        action_id=result.action_id,
                        status=verification_status,
                        before={"bytes": bytes_before, "files": files_before},
                        after={"bytes": now_bytes, "files": now_files},
                        metrics=[
                            VerificationMetric(
                                name="Temporary file size",
                                before=bytes_before,
                                after=now_bytes,
                                unit="bytes",
                                improved=is_improved,
                            ),
                            VerificationMetric(
                                name="Temporary file count",
                                before=files_before,
                                after=now_files,
                                unit="files",
                                improved=now_files <= files_before,
                            ),
                        ],
                        summary=(
                            f"Independent verification confirmed {reclaimed_bytes} bytes reclaimed across {reclaimed_files} files."
                            if verification_status == VerificationStatus.VERIFIED
                            else "Verification failed: directory size did not decrease."
                        ),
                    )
                )
            else:
                verification_results.append(
                    VerificationResult(
                        action_id=result.action_id,
                        status=VerificationStatus.SKIPPED,
                        summary="Verification is unavailable because this action has no configured Windows executor.",
                    )
                )

        return self._save(session.model_copy(update={"verification_results": verification_results, "status": SessionStatus.COMPLETED}))

