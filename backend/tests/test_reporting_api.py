from fastapi.testclient import TestClient


def viewer_headers(client: TestClient) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "report-viewer@example.com",
            "password": "report-viewer-password",
            "first_name": "Report",
            "last_name": "Viewer",
        },
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "report-viewer@example.com", "password": "report-viewer-password"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_report_endpoints_require_auth_and_return_predictable_shapes(client: TestClient) -> None:
    assert client.get("/api/v1/reports/trial-balance").status_code == 401
    headers = viewer_headers(client)
    endpoints = [
        "/api/v1/reports/trial-balance",
        "/api/v1/reports/income-statement",
        "/api/v1/reports/revenue",
        "/api/v1/reports/expenses",
        "/api/v1/reports/balance-sheet?as_of=2026-12-31",
        "/api/v1/reports/receivables?as_of=2026-12-31",
        "/api/v1/reports/payables?as_of=2026-12-31",
        "/api/v1/reports/cash-flow",
        "/api/v1/dashboard?as_of=2026-12-31",
    ]
    for endpoint in endpoints:
        response = client.get(endpoint, headers=headers)
        assert response.status_code == 200, response.text
    invalid = client.get(
        "/api/v1/reports/trial-balance?start_date=2026-12-31&end_date=2026-01-01",
        headers=headers,
    )
    assert invalid.status_code == 422
