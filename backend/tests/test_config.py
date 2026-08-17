import pytest
from backend.app.core.config import Settings
from pydantic import SecretStr, ValidationError


def test_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(  # type: ignore[call-arg]
            DATABASE_URL="sqlite+pysqlite:///:memory:",
            JWT_SECRET=SecretStr("too-short"),
            _env_file=None,
        )


def test_rejects_malformed_api_prefix() -> None:
    with pytest.raises(ValidationError, match="must start, but not end"):
        Settings(  # type: ignore[call-arg]
            DATABASE_URL="sqlite+pysqlite:///:memory:",
            JWT_SECRET=SecretStr("a-valid-test-secret-that-is-32-characters-long"),
            API_V1_PREFIX="api/v1/",
            _env_file=None,
        )


def test_bootstrap_admin_credentials_must_be_paired_and_strong() -> None:
    with pytest.raises(ValidationError, match="must be set together"):
        Settings(  # type: ignore[call-arg]
            DATABASE_URL="sqlite+pysqlite:///:memory:",
            JWT_SECRET=SecretStr("a-valid-test-secret-that-is-32-characters-long"),
            BOOTSTRAP_ADMIN_EMAIL="admin@example.com",
            _env_file=None,
        )

    with pytest.raises(ValidationError, match="12 to 128"):
        Settings(  # type: ignore[call-arg]
            DATABASE_URL="sqlite+pysqlite:///:memory:",
            JWT_SECRET=SecretStr("a-valid-test-secret-that-is-32-characters-long"),
            BOOTSTRAP_ADMIN_EMAIL="admin@example.com",
            BOOTSTRAP_ADMIN_PASSWORD=SecretStr("weak"),
            _env_file=None,
        )
