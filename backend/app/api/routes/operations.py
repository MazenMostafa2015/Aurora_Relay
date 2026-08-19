"""Authenticated operational state for the local dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..dependencies import get_current_user
from ..models import HealthRetentionResponse, HealthRetentionUpdateRequest, OperationsHealthResponse
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


@router.get("/health/retention", response_model=HealthRetentionResponse)
def get_health_retention(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> HealthRetentionResponse:
    return OperationsHealthService(db).retention(current_user)


@router.put("/health/retention", response_model=HealthRetentionResponse)
def update_health_retention(
    payload: HealthRetentionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HealthRetentionResponse:
    return OperationsHealthService(db).update_retention(current_user, payload.retention_days)
