from backend.app.core.passwords import hash_password
from backend.app.db.database import SessionLocal
from backend.app.db.models import Role, User
from fastapi.testclient import TestClient
from sqlalchemy import select


def admin_headers(client: TestClient) -> dict[str, str]:
    with SessionLocal.begin() as session:
        admin = session.scalar(select(Role).where(Role.name == "ADMIN"))
        session.add(
            User(
                email="stage3-admin@example.com",
                password_hash=hash_password("stage-three-password"),
                first_name="Stage",
                last_name="Admin",
                roles=[admin],
            )
        )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "stage3-admin@example.com", "password": "stage-three-password"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_accounting_api_requires_authentication_and_permission(client: TestClient) -> None:
    assert client.get("/api/v1/parties").status_code == 401
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "viewer@example.com",
            "password": "viewer-password-123",
            "first_name": "View",
            "last_name": "Only",
        },
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": "viewer-password-123"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/parties", headers=headers).status_code == 200
    assert client.post("/api/v1/parties", headers=headers, json={}).status_code == 403


def test_accounting_api_crud_post_and_reverse(client: TestClient) -> None:
    headers = admin_headers(client)
    party = client.post(
        "/api/v1/parties",
        headers=headers,
        json={"name": "API Customer", "is_customer": True},
    )
    assert party.status_code == 201
    assert (
        client.patch(
            f"/api/v1/parties/{party.json()['id']}", headers=headers, json={"phone": "123"}
        ).status_code
        == 200
    )
    asset = client.post(
        "/api/v1/account-categories",
        headers=headers,
        json={"name": "API Assets", "account_type": "ASSET"},
    ).json()
    revenue_category = client.post(
        "/api/v1/account-categories",
        headers=headers,
        json={"name": "API Revenue", "account_type": "REVENUE"},
    ).json()
    debit = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"code": "API-100", "name": "Cash", "category_id": asset["id"]},
    ).json()
    credit = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"code": "API-400", "name": "Revenue", "category_id": revenue_category["id"]},
    ).json()
    period = client.post(
        "/api/v1/periods",
        headers=headers,
        json={"name": "API 2026", "start_date": "2026-01-01", "end_date": "2026-12-31"},
    ).json()
    journal = client.post(
        "/api/v1/journals",
        headers=headers,
        json={
            "entry_number": "API-J-1",
            "entry_date": "2026-06-01",
            "description": "API posting",
            "period_id": period["id"],
            "lines": [
                {"account_id": debit["id"], "debit": "50", "credit": "0"},
                {"account_id": credit["id"], "debit": "0", "credit": "50"},
            ],
        },
    )
    assert journal.status_code == 201
    posted = client.post(f"/api/v1/journals/{journal.json()['id']}/post", headers=headers)
    assert posted.status_code == 200 and posted.json()["status"] == "POSTED"
    reversal = client.post(f"/api/v1/journals/{journal.json()['id']}/reverse", headers=headers)
    assert reversal.status_code == 201 and reversal.json()["reversal_of_id"] == journal.json()["id"]
