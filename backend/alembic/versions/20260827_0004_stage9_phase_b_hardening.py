"""Add semantic account roles and pin ML artifact integrity.

Revision ID: 20260827_0004
Revises: 20260825_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0004"
down_revision: str | None = "20260825_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("posting_role", sa.String(length=20), server_default="GENERAL", nullable=False),
    )
    op.create_check_constraint(
        "valid_posting_role",
        "accounts",
        "posting_role IN ('GENERAL','CASH','RECEIVABLE','REVENUE','TAX_LIABILITY')",
    )
    op.add_column(
        "ml_model_versions",
        sa.Column("artifact_digest", sa.String(length=64), nullable=True),
    )
    op.execute(
        sa.text("UPDATE ml_model_versions SET is_active = false, activated_at = NULL")
    )


def downgrade() -> None:
    op.drop_column("ml_model_versions", "artifact_digest")
    op.drop_constraint("valid_posting_role", "accounts", type_="check")
    op.drop_column("accounts", "posting_role")
