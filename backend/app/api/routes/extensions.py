"""Authenticated lifecycle APIs for reviewed local extensions."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import get_current_user
from ..models import ExtensionCatalogResponse, ExtensionExecutionResponse, ExtensionInstallRequest, ExtensionResponse, ExtensionUpdateRequest
from ...database.models import User
from ...database.session import get_db
from ...config.settings import settings
from ...services.extensions.registry import ExtensionRegistry
from ...services.extensions.service import ExtensionService, ExtensionServiceError

router = APIRouter(prefix="/extensions", tags=["Extensions"])


def service(db: Session) -> ExtensionService:
    return ExtensionService(db, registry=ExtensionRegistry(settings.extension_registry_dir))


def _raise(exc: ExtensionServiceError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/catalog", response_model=ExtensionCatalogResponse)
def get_catalog(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ExtensionCatalogResponse:
    try:
        return ExtensionCatalogResponse(extensions=service(db).catalog(current_user))
    except ExtensionServiceError as exc:
        _raise(exc)


@router.get("", response_model=list[ExtensionResponse])
def list_extensions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ExtensionResponse]:
    return [ExtensionResponse.model_validate(item) for item in service(db).list_installed(current_user)]


@router.post("", response_model=ExtensionResponse, status_code=status.HTTP_201_CREATED)
def install_extension(payload: ExtensionInstallRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ExtensionResponse:
    try:
        return ExtensionResponse.model_validate(service(db).install(current_user, payload.extension_id))
    except ExtensionServiceError as exc:
        _raise(exc)


@router.patch("/{extension_id}", response_model=ExtensionResponse)
def update_extension(extension_id: str, payload: ExtensionUpdateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ExtensionResponse:
    try:
        return ExtensionResponse.model_validate(service(db).update(current_user, extension_id, enabled=payload.enabled, configuration=payload.configuration))
    except ExtensionServiceError as exc:
        _raise(exc)


@router.post("/{extension_id}/execute", response_model=ExtensionExecutionResponse)
async def execute_extension(extension_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ExtensionExecutionResponse:
    try:
        return ExtensionExecutionResponse.model_validate(await service(db).execute(current_user, extension_id))
    except ExtensionServiceError as exc:
        _raise(exc)
