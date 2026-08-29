from typing import cast
from uuid import UUID, uuid4

from backend.app.core.passwords import hash_password
from backend.app.db.database import SessionLocal
from backend.app.db.models import AuditEvent, Role, User
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select

PASSWORD = "user-management-password-123"


def create_user(
    email: str, role_names: set[str], *, is_active: bool = True
) -> UUID:
    with SessionLocal.begin() as session:
        roles = list(session.scalars(select(Role).where(Role.name.in_(role_names))))
        user = User(
            email=email,
            password_hash=hash_password(PASSWORD),
            first_name=email.split("@", 1)[0],
            last_name="Test",
            is_active=is_active,
            roles=roles,
        )
        session.add(user)
        session.flush()
        return user.id


def login_headers(client: TestClient, email: str) -> dict[str, str]:
    response = cast(
        Response,
        client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}),
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_can_view_replace_roles_and_records_role_audit(client: TestClient) -> None:
    actor_id = create_user("admin@example.com", {"ADMIN"})
    target_id = create_user("target@example.com", {"VIEWER"})
    headers = login_headers(client, "admin@example.com")

    detail = client.get(f"/api/v1/users/{target_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["roles"] == ["VIEWER"]

    changed = client.patch(
        f"/api/v1/users/{target_id}/roles",
        headers=headers,
        json={"roles": ["MANAGER", "ACCOUNTANT"]},
    )
    assert changed.status_code == 200
    assert changed.json()["roles"] == ["ACCOUNTANT", "MANAGER"]

    with SessionLocal() as session:
        event = session.scalar(
            select(AuditEvent).where(AuditEvent.action == "identity.user.roles_changed")
        )
        assert event is not None
        assert event.actor_id == actor_id
        assert event.resource_id == str(target_id)
        assert event.details == {
            "performed_by": str(actor_id),
            "affected_user_id": str(target_id),
            "old_roles": ["VIEWER"],
            "new_roles": ["ACCOUNTANT", "MANAGER"],
        }


def test_unknown_role_rejects_entire_change(client: TestClient) -> None:
    create_user("admin@example.com", {"ADMIN"})
    target_id = create_user("target@example.com", {"VIEWER"})
    headers = login_headers(client, "admin@example.com")

    response = client.patch(
        f"/api/v1/users/{target_id}/roles",
        headers=headers,
        json={"roles": ["ACCOUNTANT", "DOES_NOT_EXIST"]},
    )
    assert response.status_code == 422
    with SessionLocal() as session:
        target = session.get(User, target_id)
        assert target is not None and target.role_names == ["VIEWER"]
        assert session.scalar(
            select(AuditEvent).where(AuditEvent.action == "identity.user.roles_changed")
        ) is None


def test_admin_can_deactivate_user_and_records_status_audit(client: TestClient) -> None:
    actor_id = create_user("admin@example.com", {"ADMIN"})
    target_id = create_user("target@example.com", {"VIEWER"})
    headers = login_headers(client, "admin@example.com")

    response = client.patch(
        f"/api/v1/users/{target_id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    with SessionLocal() as session:
        event = session.scalar(
            select(AuditEvent).where(AuditEvent.action == "identity.user.status_changed")
        )
        assert event is not None
        assert event.actor_id == actor_id
        assert event.details == {
            "performed_by": str(actor_id),
            "affected_user_id": str(target_id),
            "old_is_active": True,
            "new_is_active": False,
        }


def test_admin_cannot_deactivate_self(client: TestClient) -> None:
    admin_id = create_user("admin@example.com", {"ADMIN"})
    headers = login_headers(client, "admin@example.com")

    response = client.patch(
        f"/api/v1/users/{admin_id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert response.status_code == 409
    with SessionLocal() as session:
        admin = session.get(User, admin_id)
        assert admin is not None and admin.is_active


def test_two_active_admins_allow_removing_one_admin_role(client: TestClient) -> None:
    create_user("admin-a@example.com", {"ADMIN"})
    admin_b_id = create_user("admin-b@example.com", {"ADMIN"})
    headers = login_headers(client, "admin-a@example.com")

    response = client.patch(
        f"/api/v1/users/{admin_b_id}/roles",
        headers=headers,
        json={"roles": ["VIEWER"]},
    )
    assert response.status_code == 200
    with SessionLocal() as session:
        active_admins = session.scalars(
            select(User).join(User.roles).where(User.is_active.is_(True), Role.name == "ADMIN")
        ).all()
        assert len(active_admins) == 1
        assert active_admins[0].email == "admin-a@example.com"


def test_two_active_admins_allow_deactivating_the_other_admin(client: TestClient) -> None:
    create_user("admin-a@example.com", {"ADMIN"})
    admin_b_id = create_user("admin-b@example.com", {"ADMIN"})
    headers = login_headers(client, "admin-a@example.com")

    response = client.patch(
        f"/api/v1/users/{admin_b_id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert response.status_code == 200
    with SessionLocal() as session:
        active_admins = session.scalars(
            select(User).join(User.roles).where(User.is_active.is_(True), Role.name == "ADMIN")
        ).all()
        assert len(active_admins) == 1
        assert active_admins[0].email == "admin-a@example.com"


def test_one_active_admin_cannot_remove_own_admin_role(client: TestClient) -> None:
    admin_id = create_user("admin@example.com", {"ADMIN"})
    headers = login_headers(client, "admin@example.com")

    response = client.patch(
        f"/api/v1/users/{admin_id}/roles",
        headers=headers,
        json={"roles": ["VIEWER"]},
    )
    assert response.status_code == 409
    with SessionLocal() as session:
        admin = session.get(User, admin_id)
        assert admin is not None and admin.role_names == ["ADMIN"]


def test_user_management_requires_authentication_and_manage_permission(
    client: TestClient,
) -> None:
    target_id = create_user("target@example.com", {"VIEWER"})
    assert (
        client.patch(
            f"/api/v1/users/{uuid4()}/status", json={"is_active": False}
        ).status_code
        == 401
    )

    viewer_headers = login_headers(client, "target@example.com")
    role_response = client.patch(
        f"/api/v1/users/{target_id}/roles",
        headers=viewer_headers,
        json={"roles": ["ADMIN"]},
    )
    status_response = client.patch(
        f"/api/v1/users/{target_id}/status",
        headers=viewer_headers,
        json={"is_active": False},
    )
    assert role_response.status_code == 403
    assert status_response.status_code == 403
