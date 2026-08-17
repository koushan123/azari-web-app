from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_permission
from backend.app.db.database import get_db
from backend.app.db.models import User
from backend.app.schemas.auth import UserRead
from backend.app.services.users import UserService

router = APIRouter(prefix="/users")


@router.get("", response_model=list[UserRead])
def list_users(
    session: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("users:read"))],
) -> list[User]:
    return UserService(session).list_users()
