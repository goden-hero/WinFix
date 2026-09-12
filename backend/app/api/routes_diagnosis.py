from fastapi import APIRouter

from app.executor.registry import registry
from app.safety.privilege import is_windows_admin
from app.schemas.actions import ActionDefinition

router = APIRouter(tags=["capabilities"])


@router.get("/actions", response_model=list[ActionDefinition])
def list_actions() -> list[ActionDefinition]:
    """UI metadata only; clients cannot use this endpoint to execute an action."""
    return registry.list()


@router.get("/system/status")
def get_system_status() -> dict[str, bool]:
    """Returns system capabilities, including process elevation state."""
    return {"is_admin": is_windows_admin()}
