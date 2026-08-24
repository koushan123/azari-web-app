import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-at-least-32-characters")
os.environ.setdefault("ML_MODEL_DIR", ".test-models")

from backend.app.db.base import Base  # noqa: E402
from backend.app.db.bootstrap import seed_rbac  # noqa: E402
from backend.app.db.database import SessionLocal, engine  # noqa: E402
from backend.app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def database_schema() -> Iterator[None]:
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as session:
        seed_rbac(session)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
