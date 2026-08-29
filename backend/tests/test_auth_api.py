from typing import cast

from backend.app.core.passwords import hash_password
from backend.app.db.database import SessionLocal
from backend.app.db.models import AuditEvent, Role, User
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select

REGISTER_PAYLOAD = {
    "email": "Alice@Example.com",
    "password": "a-secure-password-123",
    "first_name": " Alice ",
    "last_name": " Example ",
}


def register(client: TestClient, **overrides: object) -> Response:
    payload = {**REGISTER_PAYLOAD, **overrides}
    return cast(Response, client.post("/api/v1/auth/register", json=payload))


def login(
    client: TestClient, email: str = "alice@example.com", password: str = "a-secure-password-123"
) -> Response:
    return cast(
        Response,
        client.post("/api/v1/auth/login", json={"email": email, "password": password}),
    )


def test_registration_normalizes_email_assigns_viewer_and_hides_password(
    client: TestClient,
) -> None:
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["phone_number"] is None
    assert body["plan_status"] == "FREE"
    assert body["roles"] == ["VIEWER"]
    assert "password" not in body
    assert "password_hash" not in body

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == "alice@example.com"))
        assert user is not None
        assert user.phone_number is None
        assert user.plan_status == "FREE"
        assert user.password_hash != REGISTER_PAYLOAD["password"]
        assert REGISTER_PAYLOAD["password"] not in user.password_hash


def test_registration_persists_optional_phone_number_and_free_plan(
    client: TestClient,
) -> None:
    response = register(client, phone_number="+989121234567")
    assert response.status_code == 201
    assert response.json()["phone_number"] == "+989121234567"
    assert response.json()["plan_status"] == "FREE"

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == "alice@example.com"))
        assert user is not None
        assert user.phone_number == "+989121234567"
        assert user.plan_status == "FREE"


def test_registration_rejects_malformed_phone_number(client: TestClient) -> None:
    for malformed in ("09121234567", "+98 9121234567", "+01234567", "+123"):
        assert register(client, phone_number=malformed).status_code == 422


def test_duplicate_phone_number_is_rejected_without_creating_second_user(
    client: TestClient,
) -> None:
    assert register(client, phone_number="+989121234567").status_code == 201
    duplicate = register(
        client,
        email="second@example.com",
        phone_number="+989121234567",
    )
    assert duplicate.status_code == 409

    with SessionLocal() as session:
        users = session.scalars(
            select(User).where(User.phone_number == "+989121234567")
        ).all()
        assert len(users) == 1
        assert users[0].email == "alice@example.com"


def test_public_registration_rejects_role_injection_and_invalid_password(
    client: TestClient,
) -> None:
    injected = register(client, roles=["ADMIN"])
    weak = register(client, password="short")
    assert injected.status_code == 422
    assert weak.status_code == 422


def test_duplicate_email_is_rejected_and_audited(client: TestClient) -> None:
    assert register(client).status_code == 201
    response = register(client, email="ALICE@example.com")
    assert response.status_code == 409

    with SessionLocal() as session:
        failures = session.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "identity.registration",
                AuditEvent.success.is_(False),
            )
        ).all()
        assert len(failures) == 1


def test_login_me_and_last_login(client: TestClient) -> None:
    register(client)
    response = login(client)
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    token = response.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == "alice@example.com"))
        assert user is not None and user.last_login_at is not None


def test_wrong_nonexistent_and_inactive_login_are_rejected_and_audited(client: TestClient) -> None:
    register(client)
    with SessionLocal.begin() as session:
        user = session.scalar(select(User).where(User.email == "alice@example.com"))
        assert user is not None
        user.is_active = False

    responses = [
        login(client, password="wrong-password"),
        login(client, email="missing@example.com"),
    ]
    assert all(response.status_code == 401 for response in responses)
    assert all(response.json()["detail"] == "Invalid email or password" for response in responses)

    with SessionLocal() as session:
        failures = session.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "identity.login", AuditEvent.success.is_(False)
            )
        ).all()
        assert len(failures) == 2
        assert "password" not in str([event.details for event in failures]).casefold()


def test_missing_malformed_and_inactive_tokens_are_unauthorized(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": "Bearer malformed"}).status_code
        == 401
    )

    register(client)
    token = login(client).json()["access_token"]
    with SessionLocal.begin() as session:
        user = session.scalar(select(User).where(User.email == "alice@example.com"))
        assert user is not None
        user.is_active = False
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code
        == 401
    )


def test_permission_enforcement_for_viewer_and_multiple_roles(client: TestClient) -> None:
    register(client)
    viewer_token = login(client).json()["access_token"]
    assert (
        client.get("/api/v1/users", headers={"Authorization": f"Bearer {viewer_token}"}).status_code
        == 403
    )

    with SessionLocal.begin() as session:
        user = session.scalar(select(User).where(User.email == "alice@example.com"))
        manager = session.scalar(select(Role).where(Role.name == "MANAGER"))
        accountant = session.scalar(select(Role).where(Role.name == "ACCOUNTANT"))
        assert user is not None and manager is not None and accountant is not None
        user.roles = [manager, accountant]

    authorized = client.get("/api/v1/users", headers={"Authorization": f"Bearer {viewer_token}"})
    assert authorized.status_code == 200
    assert authorized.json()[0]["email"] == "alice@example.com"


def test_user_with_no_roles_has_no_permissions(client: TestClient) -> None:
    with SessionLocal.begin() as session:
        user = User(
            email="noroles@example.com",
            password_hash=hash_password("a-secure-password-456"),
            first_name="No",
            last_name="Roles",
        )
        session.add(user)
    token = login(client, "noroles@example.com", "a-secure-password-456").json()["access_token"]
    assert (
        client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"}).status_code == 403
    )


def test_audit_events_never_store_credentials(client: TestClient) -> None:
    register(client)
    login(client)
    with SessionLocal() as session:
        events = session.scalars(select(AuditEvent)).all()
        serialized = " ".join(str(event.details) for event in events)
        assert REGISTER_PAYLOAD["password"] not in serialized
        assert "password_hash" not in serialized
        assert "Bearer " not in serialized


def test_login_rate_limit_returns_429_with_retry_guidance(client: TestClient) -> None:
    responses = [login(client, email="limited@example.com", password="wrong") for _ in range(6)]

    assert all(response.status_code == 401 for response in responses[:5])
    assert responses[5].status_code == 429
    assert responses[5].json() == {
        "detail": "Too many authentication attempts. Try again later."
    }
    assert int(responses[5].headers["retry-after"]) > 0


def test_registration_has_an_independent_rate_limit(client: TestClient) -> None:
    responses = [register(client) for _ in range(6)]

    assert responses[0].status_code == 201
    assert all(response.status_code == 409 for response in responses[1:5])
    assert responses[5].status_code == 429
