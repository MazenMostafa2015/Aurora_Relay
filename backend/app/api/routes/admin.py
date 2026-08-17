from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..dependencies import get_current_admin
from ..models import AdminStatsResponse
from ...database.models import AuditLog, Task, User, UserSession
from ...database.session import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/stats", response_model=AdminStatsResponse)
async def stats(_: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return AdminStatsResponse(users=db.scalar(select(func.count(User.id))) or 0, tasks=db.scalar(select(func.count(Task.id))) or 0, active_sessions=db.scalar(select(func.count(UserSession.id)).where(UserSession.is_valid.is_(True))) or 0, audit_events=db.scalar(select(func.count(AuditLog.id))) or 0)

@router.get("/users")
async def users(_: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return [{"id": u.id, "username": u.username, "email": u.email, "is_active": u.is_active, "is_admin": u.is_admin} for u in db.scalars(select(User).order_by(User.created_at.desc())).all()]
