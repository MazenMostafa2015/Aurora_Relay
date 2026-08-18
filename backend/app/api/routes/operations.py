"""Authenticated operational state for the local dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..dependencies import get_current_user
from ..models import OperationsHealthResponse
from ...database.models import User
from ...database.session import get_db
from ...services.operations_health import OperationsHealthService


router = APIRouter(prefix="/operations", tags=["Operations"])


@router.get("/health", response_model=OperationsHealthResponse)
def get_operations_health(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> OperationsHealthResponse:
    """Return the authenticated operator's bounded operational snapshot."""
    return OperationsHealthService(db).snapshot(current_user.id)
