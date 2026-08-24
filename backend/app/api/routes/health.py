from datetime import UTC, datetime

from fastapi import APIRouter

from backend.app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return liveness information without accessing external dependencies."""
    return HealthResponse(status="ok", service="backend", timestamp=datetime.now(UTC))
