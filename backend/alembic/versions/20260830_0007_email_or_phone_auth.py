"""Allow users to authenticate with either email or phone number.

Revision ID: 20260830_0007
Revises: 20260830_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0007"
down_revision: str | None = "20260830_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(length=320), nullable=True)
    op.create_check_constraint(
        "contact_method_required",
        "users",
        "email IS NOT NULL OR phone_number IS NOT NULL",
    )


def downgrade() -> None:
    connection = op.get_bind()
    phone_only_count = connection.scalar(
        sa.select(sa.func.count()).select_from(sa.table("users")).where(
            sa.column("email").is_(None)
        )
    )
    if phone_only_count:
        raise RuntimeError("Cannot downgrade while phone-only user accounts exist")
    op.drop_constraint(op.f("ck_users_contact_method_required"), "users", type_="check")
    op.alter_column("users", "email", existing_type=sa.String(length=320), nullable=False)
