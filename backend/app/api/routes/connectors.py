"""Authenticated connector-management and Revit approval routes."""
from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..dependencies import get_current_user
from ..models import (
    ConnectorActionRequest,
    ConnectorActionResponse,
    ConnectorCreate,
    ConnectorListResponse,
    ConnectorResponse,
    ConnectorUpdate,
    RevitApplyRequest,
    RevitOperationResponse,
    RevitPlanRequest,
    RevitPlanResponse,
)
from ...database.models import User
from ...database.session import get_db
from ...services.connectors import ConnectorService, ConnectorServiceError

router = APIRouter(prefix="/connectors", tags=["Connectors"])
_sensitive_operation_hits: dict[str, deque[float]] = defaultdict(deque)


def enforce_sensitive_operation_limit(user: User) -> None:
    """Bound expensive or mutating local connector requests per authenticated owner."""
    now = monotonic()
    hits = _sensitive_operation_hits[user.id]
    while hits and now - hits[0] >= 60:
        hits.popleft()
    if len(hits) >= 10:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many sensitive connector operations. Wait a minute, then retry.")
    hits.append(now)


def service(db: Session) -> ConnectorService:
    return ConnectorService(db)


def error(exc: ConnectorServiceError) -> HTTPException:
    detail = str(exc)
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND if detail == "Connector not found" else status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get("", response_model=ConnectorListResponse)
async def list_connectors(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = service(db).list_connectors(user)
    return {"connectors": items, "count": len(items)}


@router.post("", response_model=ConnectorResponse, status_code=status.HTTP_201_CREATED)
async def create_connector(data: ConnectorCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return service(db).create_connector(user, provider=data.provider.value, display_name=data.display_name, configuration=data.configuration, credential=data.credential, credential_label=data.credential_label)
    except ConnectorServiceError as exc:
        raise error(exc) from exc


@router.get("/{connector_id}", response_model=ConnectorResponse)
async def get_connector(connector_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return service(db)._public(service(db).get_connector(user, connector_id))
    except ConnectorServiceError as exc:
        raise error(exc) from exc


@router.patch("/{connector_id}", response_model=ConnectorResponse)
async def update_connector(connector_id: str, data: ConnectorUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return service(db).update_connector(user, connector_id, **data.model_dump(exclude_unset=True))
    except ConnectorServiceError as exc:
        raise error(exc) from exc


@router.delete("/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connector(connector_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        service(db).delete_connector(user, connector_id)
    except ConnectorServiceError as exc:
        raise error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{connector_id}/test", response_model=ConnectorActionResponse)
async def test_connector(connector_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_sensitive_operation_limit(user)
    try:
        return await service(db).test_connector(user, connector_id)
    except ConnectorServiceError as exc:
        raise error(exc) from exc


@router.post("/{connector_id}/actions", response_model=ConnectorActionResponse)
async def run_connector_action(connector_id: str, data: ConnectorActionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_sensitive_operation_limit(user)
    try:
        return await service(db).run_action(user, connector_id, data.action, data.input)
    except ConnectorServiceError as exc:
        raise error(exc) from exc


@router.post("/{connector_id}/revit/plan", response_model=RevitPlanResponse)
async def plan_revit_change(connector_id: str, data: RevitPlanRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_sensitive_operation_limit(user)
    try:
        return await service(db).plan_revit(user, connector_id, data.model_dump(exclude_none=True))
    except ConnectorServiceError as exc:
        raise error(exc) from exc


@router.post("/{connector_id}/revit/operations/{operation_id}/apply", response_model=RevitOperationResponse)
async def apply_revit_change(connector_id: str, operation_id: str, data: RevitApplyRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_sensitive_operation_limit(user)
    try:
        return await service(db).apply_revit(user, connector_id, operation_id, data.confirmation)
    except ConnectorServiceError as exc:
        raise error(exc) from exc
