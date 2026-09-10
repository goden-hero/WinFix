from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_session_service
from app.schemas.session import CreateSessionRequest, DiagnoseRequest, WinFixSession
from app.services.session_service import InvalidSessionStateError, SessionNotFoundError, SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _error(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND if isinstance(error, SessionNotFoundError) else status.HTTP_409_CONFLICT, detail=str(error))


@router.post("", response_model=WinFixSession, status_code=status.HTTP_201_CREATED)
def create_session(request: CreateSessionRequest, service: SessionService = Depends(get_session_service)) -> WinFixSession:
    return service.create(request)


@router.get("/{session_id}", response_model=WinFixSession)
def get_session(session_id: str, service: SessionService = Depends(get_session_service)) -> WinFixSession:
    try:
        return service.get(session_id)
    except (SessionNotFoundError, InvalidSessionStateError) as error:
        raise _error(error) from error


@router.post("/{session_id}/diagnose", response_model=WinFixSession)
async def diagnose(session_id: str, request: DiagnoseRequest, service: SessionService = Depends(get_session_service)) -> WinFixSession:
    try:
        return await service.diagnose(session_id, request)
    except (SessionNotFoundError, InvalidSessionStateError) as error:
        raise _error(error) from error
