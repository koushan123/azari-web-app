from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_permission
from backend.app.db.database import get_db
from backend.app.db.models import User
from backend.app.schemas.auth import UserRead
from backend.app.schemas.users import UserRolesUpdate, UserStatusUpdate
from backend.app.services.users import (
    UnknownRoleError,
    UserManagementConflictError,
    UserNotFoundError,
    UserService,
)

router = APIRouter(prefix="/users")


@router.get("", response_model=list[UserRead])
def list_users(
    session: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("users:read"))],
) -> list[User]:
    return UserService(session, actor).list_users()


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: UUID,
    session: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("users:read"))],
) -> User:
    try:
        return UserService(session, actor).get_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{user_id}/roles", response_model=UserRead)
def replace_user_roles(
    user_id: UUID,
    data: UserRolesUpdate,
    session: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("users:manage"))],
) -> User:
    try:
        return UserService(session, actor).replace_roles(user_id, data)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UnknownRoleError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except UserManagementConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{user_id}/status", response_model=UserRead)
def set_user_status(
    user_id: UUID,
    data: UserStatusUpdate,
    session: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("users:manage"))],
) -> User:
    try:
        return UserService(session, actor).set_status(user_id, data)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UserManagementConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
