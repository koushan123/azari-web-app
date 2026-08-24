"""Exercise Stage 3 schema and accounting behavior on the isolated PostgreSQL database."""

from datetime import date
from decimal import Decimal

from backend.app.db.bootstrap import seed_rbac
from backend.app.db.database import SessionLocal, engine
from backend.app.db.models import (
    Account,
    AccountCategory,
    FinancialPeriod,
    Party,
    Product,
    Role,
    User,
)
from backend.app.schemas.accounting import InvoiceCreate, InvoiceIssue, PaymentCreate, PaymentPost
from backend.app.services.accounting import AccountingService
from sqlalchemy import Numeric, inspect, select, text

EXPECTED_DATABASE = "azari_stage3_test"


def main() -> None:
    with engine.connect() as connection:
        database = connection.scalar(text("select current_database()"))
        if database != EXPECTED_DATABASE:
            raise RuntimeError(f"Refusing Stage 3 verification against {database!r}")
        inspector = inspect(connection)
        expected = {
            "parties",
            "products",
            "account_categories",
            "accounts",
            "financial_periods",
            "journal_entries",
            "journal_lines",
            "invoices",
            "invoice_items",
            "payments",
            "payment_allocations",
        }
        assert expected <= set(inspector.get_table_names())
        money_column = next(
            item for item in inspector.get_columns("journal_lines") if item["name"] == "debit"
        )
        money_type = money_column["type"]
        assert isinstance(money_type, Numeric)
        assert money_type.precision == 18 and money_type.scale == 2

    with SessionLocal.begin() as session:
        seed_rbac(session)
    with SessionLocal() as session:
        admin_role = session.scalar(select(Role).where(Role.name == "ADMIN"))
        actor = User(
            email="postgres-stage3@example.com",
            password_hash="unused",
            first_name="Postgres",
            last_name="Check",
            roles=[admin_role],
        )
        assets = AccountCategory(name="PG Assets", account_type="ASSET")
        revenues = AccountCategory(name="PG Revenue", account_type="REVENUE")
        session.add_all([actor, assets, revenues])
        session.flush()
        cash = Account(code="PG-100", name="Cash", category=assets)
        receivable = Account(code="PG-110", name="Receivable", category=assets)
        revenue = Account(code="PG-400", name="Revenue", category=revenues)
        period = FinancialPeriod(
            name="PG 2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)
        )
        party = Party(name="PG Customer", is_customer=True)
        product = Product(sku="PG-P", name="Service", unit_price=Decimal("33.33"))
        session.add_all([cash, receivable, revenue, period, party, product])
        session.commit()
        service = AccountingService(session, actor)
        invoice = service.create_invoice(
            InvoiceCreate(
                invoice_number="PG-I-1",
                customer_id=party.id,
                issue_date=date(2026, 5, 1),
                due_date=date(2026, 6, 1),
                items=[
                    {"product_id": product.id, "description": "Precision", "quantity": Decimal("3")}
                ],
            )
        )
        assert invoice.total == Decimal("99.99")
        service.issue_invoice(
            invoice.id,
            InvoiceIssue(receivable_account_id=receivable.id, revenue_account_id=revenue.id),
        )
        payment = service.create_payment(
            PaymentCreate(
                party_id=party.id,
                payment_date=date(2026, 5, 2),
                amount=Decimal("99.99"),
                reference="PG-PAY-1",
                method="bank",
                allocations=[{"invoice_id": invoice.id, "amount": Decimal("99.99")}],
            )
        )
        service.post_payment(
            payment.id, PaymentPost(cash_account_id=cash.id, receivable_account_id=receivable.id)
        )
        assert invoice.status == "PAID" and invoice.balance_due == 0
        assert payment.journal is not None and payment.journal.status == "POSTED"
    print("Stage 3 PostgreSQL schema, precision, invoice, payment, and ledger checks passed")


if __name__ == "__main__":
    main()
