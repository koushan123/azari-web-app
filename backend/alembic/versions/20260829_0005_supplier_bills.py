"""Add supplier bills and payable-side payments.

Revision ID: 20260829_0005
Revises: 20260827_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260829_0005"
down_revision: str | None = "20260827_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_accounts_valid_posting_role"), "accounts", type_="check")
    op.create_check_constraint(
        "valid_posting_role",
        "accounts",
        "posting_role IN "
        "('GENERAL','CASH','RECEIVABLE','REVENUE','TAX_LIABILITY','PAYABLE','EXPENSE')",
    )

    op.create_table(
        "bills",
        sa.Column("bill_number", sa.String(length=80), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="DRAFT", nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("tax", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("total", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("amount_paid", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("journal_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("issue_date <= due_date", name=op.f("ck_bills_valid_dates")),
        sa.CheckConstraint(
            "subtotal >= 0 AND tax >= 0 AND total >= 0 AND amount_paid >= 0",
            name=op.f("ck_bills_nonnegative_totals"),
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','ISSUED','PARTIALLY_PAID','PAID','CANCELLED')",
            name=op.f("ck_bills_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["parties.id"],
            name=op.f("fk_bills_supplier_id_parties"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["journal_id"],
            ["journal_entries.id"],
            name=op.f("fk_bills_journal_id_journal_entries"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bills")),
        sa.UniqueConstraint("bill_number", name="uq_bills_bill_number"),
        sa.UniqueConstraint("journal_id", name=op.f("uq_bills_journal_id")),
    )
    op.create_index(op.f("ix_bills_bill_number"), "bills", ["bill_number"])
    op.create_index("ix_bills_supplier_issue_date", "bills", ["supplier_id", "issue_date"])
    op.create_index("ix_bills_status_due_date", "bills", ["status", "due_date"])

    op.create_table(
        "bill_items",
        sa.Column("bill_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("line_subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_bill_items_positive_quantity")),
        sa.CheckConstraint(
            "unit_price >= 0 AND tax >= 0 AND line_subtotal >= 0 AND line_total >= 0",
            name=op.f("ck_bill_items_nonnegative_totals"),
        ),
        sa.ForeignKeyConstraint(
            ["bill_id"],
            ["bills.id"],
            name=op.f("fk_bill_items_bill_id_bills"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_bill_items_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bill_items")),
    )

    op.create_table(
        "bill_payments",
        sa.Column("party_id", sa.Uuid(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=12), server_default="DRAFT", nullable=False),
        sa.Column("journal_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_bill_payments_positive_amount")),
        sa.CheckConstraint(
            "status IN ('DRAFT','POSTED','CANCELLED')",
            name=op.f("ck_bill_payments_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["party_id"],
            ["parties.id"],
            name=op.f("fk_bill_payments_party_id_parties"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["journal_id"],
            ["journal_entries.id"],
            name=op.f("fk_bill_payments_journal_id_journal_entries"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bill_payments")),
        sa.UniqueConstraint("reference", name="uq_bill_payments_reference"),
        sa.UniqueConstraint("journal_id", name=op.f("uq_bill_payments_journal_id")),
    )
    op.create_index(op.f("ix_bill_payments_reference"), "bill_payments", ["reference"])
    op.create_index(
        "ix_bill_payments_party_payment_date",
        "bill_payments",
        ["party_id", "payment_date"],
    )
    op.create_index(
        "ix_bill_payments_status_payment_date",
        "bill_payments",
        ["status", "payment_date"],
    )

    op.create_table(
        "bill_payment_allocations",
        sa.Column("bill_payment_id", sa.Uuid(), nullable=False),
        sa.Column("bill_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "amount > 0", name=op.f("ck_bill_payment_allocations_positive_amount")
        ),
        sa.ForeignKeyConstraint(
            ["bill_payment_id"],
            ["bill_payments.id"],
            name=op.f("fk_bill_payment_allocations_bill_payment_id_bill_payments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["bill_id"],
            ["bills.id"],
            name=op.f("fk_bill_payment_allocations_bill_id_bills"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bill_payment_allocations")),
        sa.UniqueConstraint(
            "bill_payment_id", "bill_id", name="uq_bill_payment_allocations_pair"
        ),
    )
    op.create_index(
        "ix_bill_payment_allocations_bill_id", "bill_payment_allocations", ["bill_id"]
    )


def downgrade() -> None:
    op.drop_table("bill_payment_allocations")
    op.drop_table("bill_payments")
    op.drop_table("bill_items")
    op.drop_table("bills")
    op.drop_constraint(op.f("ck_accounts_valid_posting_role"), "accounts", type_="check")
    op.execute(
        sa.text(
            "UPDATE accounts SET posting_role = 'GENERAL' "
            "WHERE posting_role IN ('PAYABLE','EXPENSE')"
        )
    )
    op.create_check_constraint(
        "valid_posting_role",
        "accounts",
        "posting_role IN ('GENERAL','CASH','RECEIVABLE','REVENUE','TAX_LIABILITY')",
    )
