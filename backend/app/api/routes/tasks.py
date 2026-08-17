from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..dependencies import get_current_user, get_app_state
from ..models import TaskCreate, TaskListResponse, TaskResponse, TaskStatus, TaskUpdate
from ...database.models import User
from ...database.session import get_db
from ...services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])

def service(db: Session, state: dict): return TaskService(db, state.get("coordinator"))

@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(data: TaskCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db), state: dict = Depends(get_app_state)):
    return await service(db, state).create_task(user.id, data)

@router.get("", response_model=TaskListResponse)
async def list_tasks(status: TaskStatus | None = None, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tasks, total = service(db, {}).list_tasks(user.id, status, page, limit)
    return TaskListResponse(tasks=tasks, total=total, page=page, limit=limit)

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = service(db, {}).get_task(task_id, user.id)
    if not task: raise HTTPException(404, "Task not found")
    return task

@router.get("/{task_id}/status")
async def task_status(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db), state: dict = Depends(get_app_state)):
    result = await service(db, state).status(task_id, user.id)
    if result is None: raise HTTPException(404, "Task not found")
    return result

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, data: TaskUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db), state: dict = Depends(get_app_state)):
    task = await service(db, state).update_task(task_id, user.id, data)
    if not task: raise HTTPException(404, "Task not found")
    return task

@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not service(db, {}).delete_task(task_id, user.id): raise HTTPException(404, "Task not found")

@router.post("/{task_id}/pause")
async def pause_task(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db), state: dict = Depends(get_app_state)):
    return await update_task(task_id, TaskUpdate(status=TaskStatus.PAUSED), user, db, state)

@router.post("/{task_id}/resume")
async def resume_task(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = service(db, {}).get_task(task_id, user.id)
    if not task: raise HTTPException(404, "Task not found")
    task.status = TaskStatus.EXECUTING.value; db.commit(); db.refresh(task); return task

@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db), state: dict = Depends(get_app_state)):
    return await update_task(task_id, TaskUpdate(status=TaskStatus.CANCELLED), user, db, state)
