from backend.app.db.database import SessionLocal, engine
from backend.app.db.models import Permission, Role
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError


def test_stage_two_tables_and_constraints_exist() -> None:
    inspector = inspect(engine)
    assert {
        "users",
        "roles",
        "permissions",
        "user_roles",
        "role_permissions",
        "audit_events",
        "ml_model_versions",
        "ml_predictions",
        "ml_prediction_feedback",
    } <= set(inspector.get_table_names())
    assert any(
        item["name"] == "uq_users_email" for item in inspector.get_unique_constraints("users")
    )
    assert any(
        item["name"] == "uq_users_phone_number_not_null" and item["unique"]
        for item in inspector.get_indexes("users")
    )
    assert any(
        item["name"] == "ck_users_valid_plan_status"
        for item in inspector.get_check_constraints("users")
    )
    assert any(
        item["name"] == "ck_users_contact_method_required"
        for item in inspector.get_check_constraints("users")
    )


def test_rbac_bootstrap_is_idempotent() -> None:
    from backend.app.db.bootstrap import seed_rbac

    with SessionLocal.begin() as session:
        seed_rbac(session)
        seed_rbac(session)
        assert len(session.scalars(select(Role)).all()) == 4
        from backend.app.db.bootstrap import PERMISSIONS

        assert len(session.scalars(select(Permission)).all()) == len(PERMISSIONS)


def test_role_name_database_uniqueness() -> None:
    with SessionLocal() as session:
        session.add(Role(name="VIEWER", description="duplicate"))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError("database accepted a duplicate role")
