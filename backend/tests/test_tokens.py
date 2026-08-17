from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from backend.app.core.tokens import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
)


def test_valid_access_token_round_trip() -> None:
    user_id = uuid4()
    assert decode_access_token(create_access_token(user_id)) == user_id


@pytest.mark.parametrize("token", ["malformed", "", "a.b.c"])
def test_rejects_invalid_tokens(token: str) -> None:
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)


def test_rejects_expired_token() -> None:
    expired_at = datetime.now(UTC) - timedelta(days=1)
    token = create_access_token(uuid4(), now=expired_at)
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)
