"""Scope accounting data to private user workspaces.

Revision ID: 20260901_0010
Revises: 20260830_0009
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_0010"
down_revision: str | None = "20260830_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OWNED_TABLES = (
    "parties",
    "products",
    "account_categories",
    "accounts",
    "financial_periods",
    "journal_entries",
    "invoices",
    "invoice_checks",
    "bills",
    "payments",
    "bill_payments",
)

PER_USER_UNIQUES = {
    "products": ("uq_products_sku", ("owner_id", "sku")),
    "account_categories": (
        "uq_account_categories_name",
        ("owner_id", "name"),
    ),
    "accounts": ("uq_accounts_code", ("owner_id", "code")),
    "financial_periods": (
        "uq_financial_periods_name",
        ("owner_id", "name"),
    ),
    "journal_entries": (
        "uq_journal_entries_entry_number",
        ("owner_id", "entry_number"),
    ),
    "invoices": (
        "uq_invoices_invoice_number",
        ("owner_id", "invoice_number"),
    ),
    "invoice_checks": (
        "uq_invoice_checks_sayad_id",
        ("owner_id", "sayad_id"),
    ),
    "bills": ("uq_bills_bill_number", ("owner_id", "bill_number")),
    "payments": ("uq_payments_reference", ("owner_id", "reference")),
    "bill_payments": (
        "uq_bill_payments_reference",
        ("owner_id", "reference"),
    ),
}


def _creator_id(connection: sa.Connection) -> object | None:
    creator_email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip().casefold()
    if not creator_email:
        return None
    return connection.execute(
        sa.text("SELECT id FROM users WHERE lower(email) = :email"),
        {"email": creator_email},
    ).scalar_one_or_none()


def upgrade() -> None:
    connection = op.get_bind()
    for table in OWNED_TABLES:
        op.add_column(table, sa.Column("owner_id", sa.Uuid(), nullable=True))

    existing_rows = sum(
        int(connection.execute(sa.text(f'SELECT count(*) FROM "{table}"')).scalar_one())
        for table in OWNED_TABLES
    )
    creator_id = _creator_id(connection)
    if existing_rows and creator_id is None:
        raise RuntimeError(
            "Existing accounting data requires BOOTSTRAP_ADMIN_EMAIL to identify its owner"
        )
    if creator_id is not None:
        for table in OWNED_TABLES:
            connection.execute(
                sa.text(f'UPDATE "{table}" SET owner_id = :owner_id'),
                {"owner_id": creator_id},
            )
        connection.execute(
            sa.text(
                "UPDATE ml_predictions SET requested_by_id = :owner_id "
                "WHERE requested_by_id IS NULL"
            ),
            {"owner_id": creator_id},
        )

    for table in OWNED_TABLES:
        op.alter_column(table, "owner_id", existing_type=sa.Uuid(), nullable=False)
        op.create_foreign_key(
            op.f(f"fk_{table}_owner_id_users"),
            table,
            "users",
            ["owner_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(op.f(f"ix_{table}_owner_id"), table, ["owner_id"])

    for table, (constraint, columns) in PER_USER_UNIQUES.items():
        op.drop_constraint(op.f(constraint), table, type_="unique")
        op.create_unique_constraint(constraint, table, list(columns))


def downgrade() -> None:
    original_columns = {
        "products": ("sku",),
        "account_categories": ("name",),
        "accounts": ("code",),
        "financial_periods": ("name",),
        "journal_entries": ("entry_number",),
        "invoices": ("invoice_number",),
        "invoice_checks": ("sayad_id",),
        "bills": ("bill_number",),
        "payments": ("reference",),
        "bill_payments": ("reference",),
    }
    for table, (constraint, _) in reversed(tuple(PER_USER_UNIQUES.items())):
        op.drop_constraint(op.f(constraint), table, type_="unique")
        op.create_unique_constraint(constraint, table, list(original_columns[table]))

    for table in reversed(OWNED_TABLES):
        op.drop_index(op.f(f"ix_{table}_owner_id"), table_name=table)
        op.drop_constraint(
            op.f(f"fk_{table}_owner_id_users"), table, type_="foreignkey"
        )
        op.drop_column(table, "owner_id")
