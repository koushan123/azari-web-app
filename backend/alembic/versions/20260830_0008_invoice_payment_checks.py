"""Add invoice payment method and check tracking.

Revision ID: 20260830_0008
Revises: 20260830_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0008"
down_revision: str | None = "20260830_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("payment_method", sa.String(length=10)))
    op.create_check_constraint(
        "valid_payment_method",
        "invoices",
        "payment_method IS NULL OR payment_method IN ('CASH','CHECK')",
    )
    op.create_table(
        "invoice_checks",
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("sayad_id", sa.String(length=32), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=12), server_default="PENDING", nullable=False),
        sa.Column("cleared_date", sa.Date()),
        sa.Column("cleared_payment_id", sa.Uuid()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_invoice_checks_positive_amount")),
        sa.CheckConstraint(
            "status IN ('PENDING','CLEARED','BOUNCED')",
            name=op.f("ck_invoice_checks_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["cleared_payment_id"], ["payments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoice_checks")),
        sa.UniqueConstraint(
            "cleared_payment_id", name=op.f("uq_invoice_checks_cleared_payment_id")
        ),
        sa.UniqueConstraint("sayad_id", name="uq_invoice_checks_sayad_id"),
    )
    op.create_index("ix_invoice_checks_invoice_id", "invoice_checks", ["invoice_id"])
    op.create_index(
        "ix_invoice_checks_status_due_date", "invoice_checks", ["status", "due_date"]
    )


def downgrade() -> None:
    op.drop_index("ix_invoice_checks_status_due_date", table_name="invoice_checks")
    op.drop_index("ix_invoice_checks_invoice_id", table_name="invoice_checks")
    op.drop_table("invoice_checks")
    op.drop_constraint(op.f("ck_invoices_valid_payment_method"), "invoices", type_="check")
    op.drop_column("invoices", "payment_method")
