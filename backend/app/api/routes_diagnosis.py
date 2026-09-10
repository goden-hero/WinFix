from fastapi import APIRouter

from app.executor.registry import registry
from app.schemas.actions import ActionDefinition

router = APIRouter(tags=["capabilities"])


@router.get("/actions", response_model=list[ActionDefinition])
def list_actions() -> list[ActionDefinition]:
    """UI metadata only; clients cannot use this endpoint to execute an action."""
    return registry.list()
