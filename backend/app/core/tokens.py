from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

from backend.app.core.config import get_settings


class InvalidAccessTokenError(ValueError):
    """Raised when an access token cannot be trusted."""


def create_access_token(user_id: UUID, *, now: datetime | None = None) -> str:
    settings = get_settings()
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": issued_at,
        "exp": expires_at,
        "jti": str(uuid4()),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "type", "iat", "exp", "jti"]},
        )
        if payload.get("type") != "access":
            raise InvalidAccessTokenError("Invalid token type")
        return UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError) as exc:
        raise InvalidAccessTokenError("Invalid or expired access token") from exc
