"""Add customer credit posting role and optional payment Sayad IDs.

Revision ID: 20260830_0009
Revises: 20260830_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0009"
down_revision: str | None = "20260830_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_accounts_valid_posting_role"), "accounts", type_="check")
    op.create_check_constraint(
        "valid_posting_role",
        "accounts",
        "posting_role IN "
        "('GENERAL','CASH','RECEIVABLE','REVENUE','TAX_LIABILITY','PAYABLE','EXPENSE',"
        "'CUSTOMER_CREDIT')",
    )
    op.add_column("payments", sa.Column("sayad_id", sa.String(length=100), nullable=True))
    op.add_column(
        "payments", sa.Column("customer_credit_account_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_payments_customer_credit_account_id_accounts"),
        "payments",
        "accounts",
        ["customer_credit_account_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column("bill_payments", sa.Column("sayad_id", sa.String(length=100), nullable=True))
    op.alter_column("invoice_checks", "sayad_id", existing_type=sa.String(length=32), nullable=True)


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE invoice_checks SET sayad_id = "
            "'LEGACY-' || substr(replace(id::text, '-', ''), 1, 25) "
            "WHERE sayad_id IS NULL"
        )
    )
    op.alter_column(
        "invoice_checks",
        "sayad_id",
        existing_type=sa.String(length=32),
        nullable=False,
    )
    op.drop_column("bill_payments", "sayad_id")
    op.drop_constraint(
        op.f("fk_payments_customer_credit_account_id_accounts"),
        "payments",
        type_="foreignkey",
    )
    op.drop_column("payments", "customer_credit_account_id")
    op.drop_column("payments", "sayad_id")
    op.drop_constraint(op.f("ck_accounts_valid_posting_role"), "accounts", type_="check")
    op.execute(
        sa.text(
            "UPDATE accounts SET posting_role = 'GENERAL' "
            "WHERE posting_role = 'CUSTOMER_CREDIT'"
        )
    )
    op.create_check_constraint(
        "valid_posting_role",
        "accounts",
        "posting_role IN "
        "('GENERAL','CASH','RECEIVABLE','REVENUE','TAX_LIABILITY','PAYABLE','EXPENSE')",
    )
