from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings


def create_database_engine(database_url: str) -> Engine:
    """Create an engine with safe defaults and deterministic in-memory test behavior."""
    options: dict[str, object] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite") and ":memory:" in database_url:
        options.update(
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(database_url, **options)


engine = create_database_engine(get_settings().DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Provide one SQLAlchemy session per request."""
    with SessionLocal() as session:
        yield session
