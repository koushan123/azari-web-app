from backend.app.main import app
from fastapi.testclient import TestClient


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "backend"


def test_readiness_check_queries_required_database() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "backend"
