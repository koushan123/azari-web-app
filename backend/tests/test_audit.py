import pytest
from backend.app.db.database import SessionLocal
from backend.app.repositories.audit import AuditRepository


@pytest.mark.parametrize(
    "details",
    [
        {"password": "not-allowed"},
        {"nested": {"access_token": "not-allowed"}},
        {"items": [{"authorization": "Bearer not-allowed"}]},
    ],
)
def test_audit_repository_rejects_sensitive_metadata(details: dict[str, object]) -> None:
    with SessionLocal() as session, pytest.raises(ValueError, match="Sensitive values"):
        AuditRepository(session).record(
            action="security.test",
            resource_type="test",
            success=False,
            details=details,
        )
