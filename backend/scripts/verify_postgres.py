"""Run destructive schema checks only against the dedicated Stage 2 test database."""

from backend.app.core.passwords import hash_password
from backend.app.db.database import SessionLocal, engine
from backend.app.db.models import Role, User
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

EXPECTED_DATABASE = "azari_stage2_test"


def main() -> None:
    if engine.dialect.name != "postgresql" or engine.url.database != EXPECTED_DATABASE:
        raise RuntimeError(
            "PostgreSQL verification requires the isolated azari_stage2_test database"
        )

    inspector = inspect(engine)
    expected_tables = {
        "users",
        "roles",
        "permissions",
        "user_roles",
        "role_permissions",
        "audit_events",
        "alembic_version",
    }
    if not expected_tables <= set(inspector.get_table_names()):
        raise RuntimeError("Migrated PostgreSQL schema is incomplete")

    unique_names = {item["name"] for item in inspector.get_unique_constraints("users")}
    if "uq_users_email" not in unique_names:
        raise RuntimeError("PostgreSQL users.email uniqueness constraint is missing")

    with SessionLocal.begin() as session:
        viewer = session.scalar(select(Role).where(Role.name == "VIEWER"))
        if viewer is None:
            raise RuntimeError("Idempotent RBAC bootstrap did not create VIEWER")
        user = User(
            email="postgres-verification@example.com",
            password_hash=hash_password("postgres-verification-password"),
            first_name="PostgreSQL",
            last_name="Verification",
            roles=[viewer],
        )
        session.add(user)
        session.flush()
        session.refresh(user)
        if user.created_at.tzinfo is None or user.updated_at.tzinfo is None:
            raise RuntimeError("PostgreSQL timestamps are not timezone-aware")

    with SessionLocal() as session:
        session.add(
            User(
                email="postgres-verification@example.com",
                password_hash=hash_password("another-verification-password"),
                first_name="Duplicate",
                last_name="Verification",
            )
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
        else:
            raise RuntimeError("PostgreSQL accepted a duplicate users.email value")

    print("PostgreSQL Stage 2 schema, timestamps, RBAC, and uniqueness verified")


if __name__ == "__main__":
    main()
