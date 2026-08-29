"""Add optional user phone number and plan-status placeholder.

Revision ID: 20260830_0006
Revises: 20260829_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0006"
down_revision: str | None = "20260829_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_number", sa.String(length=32), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "plan_status",
            sa.String(length=20),
            server_default="FREE",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "valid_plan_status",
        "users",
        "plan_status IN ('FREE','PRO')",
    )
    op.create_index(
        "uq_users_phone_number_not_null",
        "users",
        ["phone_number"],
        unique=True,
        postgresql_where=sa.text("phone_number IS NOT NULL"),
        sqlite_where=sa.text("phone_number IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_phone_number_not_null", table_name="users")
    op.drop_constraint(op.f("ck_users_valid_plan_status"), "users", type_="check")
    op.drop_column("users", "plan_status")
    op.drop_column("users", "phone_number")
