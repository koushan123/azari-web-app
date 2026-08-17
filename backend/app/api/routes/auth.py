from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_authenticated_user
from backend.app.db.database import get_db
from backend.app.db.models import User
from backend.app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead
from backend.app.services.authentication import (
    AuthenticationError,
    AuthenticationService,
    DuplicateEmailError,
)

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, session: Annotated[Session, Depends(get_db)]) -> User:
    try:
        return AuthenticationService(session).register(data)
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, session: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    try:
        _, token = AuthenticationService(session).login(data)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
def me(current_user: Annotated[User, Depends(require_authenticated_user)]) -> User:
    return current_user
