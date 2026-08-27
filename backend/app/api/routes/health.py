from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return liveness information without accessing external dependencies."""
    return HealthResponse(status="ok", service="backend", timestamp=datetime.now(UTC))


@router.get("/ready", response_model=HealthResponse)
def readiness_check(session: Annotated[Session, Depends(get_db)]) -> HealthResponse:
    """Return readiness only when required database access succeeds."""
    session.execute(text("SELECT 1"))
    return HealthResponse(status="ok", service="backend", timestamp=datetime.now(UTC))
