"""Add indexes for Stage 4 report filters.

Revision ID: 20260818_0002
Revises: cd6670d77e70
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260818_0002"
down_revision: str | None = "cd6670d77e70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_journal_entries_status_entry_date",
        "journal_entries",
        ["status", "entry_date"],
    )
    op.create_index(
        "ix_invoices_customer_issue_date",
        "invoices",
        ["customer_id", "issue_date"],
    )
    op.create_index("ix_invoices_status_due_date", "invoices", ["status", "due_date"])
    op.create_index(
        "ix_payments_party_payment_date",
        "payments",
        ["party_id", "payment_date"],
    )
    op.create_index(
        "ix_payments_status_payment_date",
        "payments",
        ["status", "payment_date"],
    )
    op.create_index(
        "ix_payment_allocations_invoice_id",
        "payment_allocations",
        ["invoice_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_payment_allocations_invoice_id", table_name="payment_allocations")
    op.drop_index("ix_payments_status_payment_date", table_name="payments")
    op.drop_index("ix_payments_party_payment_date", table_name="payments")
    op.drop_index("ix_invoices_status_due_date", table_name="invoices")
    op.drop_index("ix_invoices_customer_issue_date", table_name="invoices")
    op.drop_index("ix_journal_entries_status_entry_date", table_name="journal_entries")
