from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..dependencies import get_current_user, get_token
from ..models import TokenResponse, UserLogin, UserRegister, UserResponse
from ...database.models import User
from ...database.session import get_db
from ...services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(or_(User.username == data.username, User.email == data.email))):
        raise HTTPException(400, "Username or email already exists")
    user = User(username=data.username, email=data.email, password_hash=AuthService.hash_password(data.password))
    db.add(user); db.commit(); db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))
    if not user or not AuthService.verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    token, expires = AuthService(db).create_access_token(user.id)
    AuthService(db).create_session(user, token, request.client.host if request.client else None, request.headers.get("user-agent"))
    return TokenResponse(access_token=token, expires_in=expires, user_id=user.id)

@router.post("/logout")
async def logout(token: str = Depends(get_token), db: Session = Depends(get_db)):
    AuthService(db).revoke_session(token); return {"message": "Logged out successfully"}

@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, user: User = Depends(get_current_user), token: str = Depends(get_token), db: Session = Depends(get_db)):
    service = AuthService(db); service.revoke_session(token); new_token, expires = service.create_access_token(user.id); service.create_session(user, new_token, request.client.host if request.client else None, request.headers.get("user-agent"))
    return TokenResponse(access_token=new_token, expires_in=expires, user_id=user.id)

@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)): return user
