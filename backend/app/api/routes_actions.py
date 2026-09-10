from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_session_service
from app.schemas.actions import ApprovalRequest
from app.schemas.session import WinFixSession
from app.services.session_service import InvalidSessionStateError, SessionNotFoundError, SessionService

router = APIRouter(prefix="/sessions", tags=["actions"])


def _raise(error: Exception) -> None:
    code = status.HTTP_404_NOT_FOUND if isinstance(error, SessionNotFoundError) else status.HTTP_409_CONFLICT
    raise HTTPException(status_code=code, detail=str(error)) from error


@router.post("/{session_id}/approve", response_model=WinFixSession)
def approve(session_id: str, request: ApprovalRequest, service: SessionService = Depends(get_session_service)) -> WinFixSession:
    try:
        return service.approve(session_id, request)
    except (SessionNotFoundError, InvalidSessionStateError, ValueError) as error:
        _raise(error)


@router.post("/{session_id}/reject", response_model=WinFixSession)
def reject(session_id: str, request: ApprovalRequest, service: SessionService = Depends(get_session_service)) -> WinFixSession:
    try:
        rejected = request.model_copy(update={"decisions": [item.model_copy(update={"approved": False}) for item in request.decisions]})
        return service.approve(session_id, rejected)
    except (SessionNotFoundError, InvalidSessionStateError, ValueError) as error:
        _raise(error)


@router.post("/{session_id}/execute", response_model=WinFixSession)
def execute(session_id: str, service: SessionService = Depends(get_session_service)) -> WinFixSession:
    try:
        return service.execute(session_id)
    except (SessionNotFoundError, InvalidSessionStateError, ValueError) as error:
        _raise(error)


@router.post("/{session_id}/verify", response_model=WinFixSession)
def verify(session_id: str, service: SessionService = Depends(get_session_service)) -> WinFixSession:
    try:
        return service.verify(session_id)
    except (SessionNotFoundError, InvalidSessionStateError, ValueError) as error:
        _raise(error)
