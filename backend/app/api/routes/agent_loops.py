from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import get_current_user
from ..models import (
    AgentLoopCreate,
    AgentLoopIterationListResponse,
    AgentLoopIterationResponse,
    AgentLoopListResponse,
    AgentLoopResponse,
    AgentLoopUpdate,
)
from ...database.models import User
from ...database.session import get_db
from ...services.agent_loop import AgentLoopService, AgentLoopServiceError


router = APIRouter(prefix="/agent-loops", tags=["Agent loops"])


def service(db: Session) -> AgentLoopService:
    return AgentLoopService(db)


def error(exc: AgentLoopServiceError) -> HTTPException:
    detail = str(exc)
    code = status.HTTP_404_NOT_FOUND if detail in {"Agent loop not found", "Agent loop iteration not found"} else status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=code, detail=detail)


@router.get("", response_model=AgentLoopListResponse)
async def list_loops(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    loops = service(db).list_loops(user)
    return {"loops": loops, "count": len(loops)}


@router.post("", response_model=AgentLoopResponse, status_code=status.HTTP_201_CREATED)
async def create_loop(data: AgentLoopCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return service(db).create_loop(user, name=data.name, config=data.config.model_dump())
    except AgentLoopServiceError as exc:
        raise error(exc) from exc


@router.get("/{loop_id}", response_model=AgentLoopResponse)
async def get_loop(loop_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return service(db).get_loop(user, loop_id)
    except AgentLoopServiceError as exc:
        raise error(exc) from exc


@router.patch("/{loop_id}", response_model=AgentLoopResponse)
async def update_loop(loop_id: str, data: AgentLoopUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return service(db).update_loop(user, loop_id, **data.model_dump(exclude_unset=True))
    except AgentLoopServiceError as exc:
        raise error(exc) from exc


@router.post("/{loop_id}/start", response_model=AgentLoopResponse)
async def start_loop(loop_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return service(db).start(user, loop_id)
    except AgentLoopServiceError as exc:
        raise error(exc) from exc


@router.post("/{loop_id}/pause", response_model=AgentLoopResponse)
async def pause_loop(loop_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return service(db).pause(user, loop_id)
    except AgentLoopServiceError as exc:
        raise error(exc) from exc


@router.post("/{loop_id}/hard-stop", response_model=AgentLoopResponse)
async def hard_stop_loop(loop_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return service(db).hard_stop_loop(user, loop_id)
    except AgentLoopServiceError as exc:
        raise error(exc) from exc


@router.post("/{loop_id}/run-dry", response_model=AgentLoopIterationResponse)
async def run_dry_iteration(loop_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return service(db).run_dry_iteration(user, loop_id)
    except AgentLoopServiceError as exc:
        raise error(exc) from exc


@router.get("/{loop_id}/iterations", response_model=AgentLoopIterationListResponse)
async def list_iterations(loop_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        iterations = service(db).list_iterations(user, loop_id)
        return {"iterations": iterations, "count": len(iterations)}
    except AgentLoopServiceError as exc:
        raise error(exc) from exc


@router.get("/{loop_id}/iterations/{iteration_id}/report", response_model=AgentLoopIterationResponse)
async def get_iteration_report(loop_id: str, iteration_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return service(db).get_report(user, loop_id, iteration_id)
    except AgentLoopServiceError as exc:
        raise error(exc) from exc
