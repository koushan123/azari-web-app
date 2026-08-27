from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest
from backend.app.db.database import SessionLocal, engine
from backend.app.db.models import (
    Account,
    AccountCategory,
    AuditEvent,
    FinancialPeriod,
    Invoice,
    JournalEntry,
    Party,
    Product,
    Role,
    User,
)
from backend.app.schemas.accounting import (
    AccountCreate,
    AccountUpdate,
    CategoryCreate,
    InvoiceCreate,
    InvoiceIssue,
    JournalCreate,
    PartyCreate,
    PartyUpdate,
    PaymentCreate,
    PaymentPost,
    PeriodCreate,
    ProductCreate,
    ProductUpdate,
)
from backend.app.services.accounting import (
    AccountingError,
    AccountingService,
    ConflictError,
    NotFoundError,
)
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import event, select
from sqlalchemy.orm import Session


@dataclass
class Domain:
    admin: User
    cash: Account
    receivable: Account
    revenue: Account
    period: FinancialPeriod
    customer: Party
    product: Product


def domain(session: Session) -> tuple[AccountingService, Domain]:
    admin = User(
        email="accounting@example.com",
        password_hash="not-used",
        first_name="Stage",
        last_name="Three",
        roles=[session.scalar(select(Role).where(Role.name == "ADMIN"))],
    )
    asset = AccountCategory(name="Assets", account_type="ASSET")
    revenue_category = AccountCategory(name="Revenue", account_type="REVENUE")
    session.add_all([admin, asset, revenue_category])
    session.flush()
    cash = Account(code="1000", name="Cash", category=asset)
    receivable = Account(code="1100", name="Receivable", category=asset)
    revenue = Account(code="4000", name="Sales", category=revenue_category)
    period = FinancialPeriod(name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    customer = Party(name="Customer", is_customer=True)
    product = Product(sku="P-1", name="Service", unit="hour", unit_price=Decimal("100.00"))
    session.add_all([cash, receivable, revenue, period, customer, product])
    session.commit()
    return AccountingService(session, admin), Domain(
        admin, cash, receivable, revenue, period, customer, product
    )


def journal_data(
    values: Domain,
    *,
    debit: Decimal = Decimal("100"),
    credit: Decimal = Decimal("100"),
    one_line: bool = False,
) -> JournalCreate:
    lines = [{"account_id": values.cash.id, "debit": debit, "credit": 0}]
    if not one_line:
        lines.append({"account_id": values.revenue.id, "debit": 0, "credit": credit})
    return JournalCreate(
        entry_number="J-1",
        entry_date=date(2026, 2, 1),
        description="Test journal",
        period_id=values.period.id,
        lines=lines,
    )


def invoice_data(values: Domain, number: str = "I-1") -> InvoiceCreate:
    return InvoiceCreate(
        invoice_number=number,
        customer_id=values.customer.id,
        issue_date=date(2026, 2, 1),
        due_date=date(2026, 3, 1),
        items=[
            {
                "product_id": values.product.id,
                "description": "Consulting",
                "quantity": Decimal("2.5"),
                "tax": Decimal("25"),
            }
        ],
    )


def test_balanced_posting_and_reversal_preserve_original() -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        journal = service.create_journal(journal_data(values))
        assert service.post_journal(journal.id).status == "POSTED"
        reversal = service.reverse_journal(journal.id)
        assert reversal.status == "POSTED"
        assert reversal.reversal_of_id == journal.id
        assert sum(line.debit for line in reversal.lines) == sum(
            line.credit for line in reversal.lines
        )
        assert journal.status == "POSTED"
        assert journal.lines[0].debit == Decimal("100")


def test_reversal_cannot_be_repeated_or_reversed() -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        original = service.create_journal(journal_data(values))
        service.post_journal(original.id)
        reversal = service.reverse_journal(original.id)

        with pytest.raises(ConflictError, match="already been reversed"):
            service.reverse_journal(original.id)
        with pytest.raises(ConflictError, match="cannot be reversed"):
            service.reverse_journal(reversal.id)

        assert len(session.scalars(select(JournalEntry)).all()) == 2


@pytest.mark.parametrize(
    ("debit", "credit", "one_line", "message"),
    [
        (Decimal("100"), Decimal("50"), False, "balance"),
        (Decimal("100"), Decimal("100"), True, "at least two"),
    ],
)
def test_invalid_journals_roll_back(
    debit: Decimal, credit: Decimal, one_line: bool, message: str
) -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        journal = service.create_journal(
            journal_data(values, debit=debit, credit=credit, one_line=one_line)
        )
        with pytest.raises(AccountingError, match=message):
            service.post_journal(journal.id)
        persisted = session.get(JournalEntry, journal.id)
        assert persisted is not None and persisted.status == "DRAFT"


@pytest.mark.parametrize(
    ("debit", "credit"),
    [(Decimal("0"), Decimal("0")), (Decimal("10"), Decimal("10")), (Decimal("-1"), Decimal("0"))],
)
def test_line_amount_rules(debit: Decimal, credit: Decimal) -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        with pytest.raises(ValueError):
            data = JournalCreate(
                entry_number="INVALID",
                entry_date=date(2026, 2, 1),
                description="Invalid line",
                period_id=values.period.id,
                lines=[{"account_id": values.cash.id, "debit": debit, "credit": credit}],
            )
            service.create_journal(data)


def test_inactive_account_and_closed_period_reject_posting() -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        journal = service.create_journal(journal_data(values))
        values.cash.is_active = False
        session.commit()
        with pytest.raises(ConflictError, match="Inactive"):
            service.post_journal(journal.id)
        values.cash.is_active = True
        values.period.status = "CLOSED"
        session.commit()
        with pytest.raises(ConflictError, match="closed"):
            service.post_journal(journal.id)


def test_posted_journal_has_no_mutation_or_delete_api(client: TestClient) -> None:
    assert client.patch("/api/v1/journals/00000000-0000-0000-0000-000000000000").status_code == 405
    assert client.delete("/api/v1/journals/00000000-0000-0000-0000-000000000000").status_code == 405


def test_invoice_totals_issue_and_failed_issue_are_atomic() -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        invoice = service.create_invoice(invoice_data(values))
        assert invoice.status == "DRAFT" and invoice.journal_id is None
        assert invoice.subtotal == Decimal("250.00")
        assert invoice.total == Decimal("275.00")
        issued = service.issue_invoice(
            invoice.id,
            InvoiceIssue(
                receivable_account_id=values.receivable.id,
                revenue_account_id=values.revenue.id,
            ),
        )
        assert issued.status == "ISSUED"
        assert issued.journal is not None
        assert sum(line.debit for line in issued.journal.lines) == issued.total
        assert next(
            line.credit
            for line in issued.journal.lines
            if line.account_id == values.revenue.id
        ) == Decimal("275.00")
        with pytest.raises(ConflictError, match="Source-document"):
            service.reverse_journal(issued.journal.id)
        failed = service.create_invoice(invoice_data(values, "I-2"))
        values.revenue.is_active = False
        session.commit()
        before = len(session.scalars(select(JournalEntry)).all())
        with pytest.raises(ConflictError):
            service.issue_invoice(
                failed.id,
                InvoiceIssue(
                    receivable_account_id=values.receivable.id,
                    revenue_account_id=values.revenue.id,
                ),
            )
        persisted = session.get(Invoice, failed.id)
        assert persisted is not None and persisted.status == "DRAFT"
        assert len(session.scalars(select(JournalEntry)).all()) == before


def test_invoice_issue_requires_distinct_asset_receivable_and_revenue_accounts() -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        invoice = service.create_invoice(invoice_data(values))

        with pytest.raises(AccountingError, match="different"):
            service.issue_invoice(
                invoice.id,
                InvoiceIssue(
                    receivable_account_id=values.receivable.id,
                    revenue_account_id=values.receivable.id,
                ),
            )
        with pytest.raises(AccountingError, match="REVENUE"):
            service.issue_invoice(
                invoice.id,
                InvoiceIssue(
                    receivable_account_id=values.receivable.id,
                    revenue_account_id=values.cash.id,
                ),
            )

        session.refresh(invoice)
        assert invoice.status == "DRAFT" and invoice.journal_id is None


def post_invoice(service: AccountingService, values: Domain, number: str = "I-1") -> Invoice:
    invoice = service.create_invoice(invoice_data(values, number))
    return service.issue_invoice(
        invoice.id,
        InvoiceIssue(
            receivable_account_id=values.receivable.id, revenue_account_id=values.revenue.id
        ),
    )


def payment_data(
    values: Domain, invoice: Invoice, amount: Decimal, reference: str
) -> PaymentCreate:
    return PaymentCreate(
        party_id=values.customer.id,
        payment_date=date(2026, 2, 5),
        amount=amount,
        reference=reference,
        method="bank",
        allocations=[{"invoice_id": invoice.id, "amount": amount}],
    )


def test_partial_and_full_payments_post_through_same_ledger() -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        invoice = post_invoice(service, values)
        first = service.create_payment(payment_data(values, invoice, Decimal("100"), "P-1"))
        service.post_payment(
            first.id,
            PaymentPost(cash_account_id=values.cash.id, receivable_account_id=values.receivable.id),
        )
        assert invoice.amount_paid == Decimal("100.00")
        assert invoice.status == "PARTIALLY_PAID"
        second = service.create_payment(payment_data(values, invoice, Decimal("175"), "P-2"))
        service.post_payment(
            second.id,
            PaymentPost(cash_account_id=values.cash.id, receivable_account_id=values.receivable.id),
        )
        assert invoice.balance_due == 0 and invoice.status == "PAID"
        assert second.journal is not None
        assert second.journal.status == "POSTED"
        assert sum(line.debit for line in second.journal.lines) == sum(
            line.credit for line in second.journal.lines
        )
        with pytest.raises(ConflictError, match="Source-document"):
            service.reverse_journal(second.journal.id)


def test_payment_post_requires_distinct_accounts_and_matching_invoice_receivable() -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        invoice = post_invoice(service, values)
        payment = service.create_payment(
            payment_data(values, invoice, Decimal("100"), "ACCOUNT-CHECK")
        )

        with pytest.raises(AccountingError, match="different"):
            service.post_payment(
                payment.id,
                PaymentPost(
                    cash_account_id=values.receivable.id,
                    receivable_account_id=values.receivable.id,
                ),
            )
        other_receivable = Account(
            code="1199",
            name="Other receivable",
            category=values.receivable.category,
        )
        session.add(other_receivable)
        session.commit()
        with pytest.raises(AccountingError, match="match the invoice"):
            service.post_payment(
                payment.id,
                PaymentPost(
                    cash_account_id=values.cash.id,
                    receivable_account_id=other_receivable.id,
                ),
            )

        session.refresh(payment)
        session.refresh(invoice)
        assert payment.status == "DRAFT" and payment.journal_id is None
        assert invoice.amount_paid == 0 and invoice.status == "ISSUED"


def test_payment_post_locks_payment_and_invoice_rows_before_allocation() -> None:
    locked_selects = 0

    def count_locks(*args: object) -> None:
        nonlocal locked_selects
        clause = args[1]
        if getattr(clause, "_for_update_arg", None) is not None:
            locked_selects += 1

    event.listen(engine, "before_execute", count_locks)
    try:
        with SessionLocal() as session:
            service, values = domain(session)
            invoice = post_invoice(service, values)
            payment = service.create_payment(
                payment_data(values, invoice, Decimal("100"), "LOCK-CHECK")
            )
            service.post_payment(
                payment.id,
                PaymentPost(
                    cash_account_id=values.cash.id,
                    receivable_account_id=values.receivable.id,
                ),
            )
    finally:
        event.remove(engine, "before_execute", count_locks)

    assert locked_selects >= 2


def test_payment_overallocation_invalid_sum_and_cancelled_invoice_fail() -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        invoice = post_invoice(service, values)
        with pytest.raises(AccountingError, match="balance"):
            service.create_payment(payment_data(values, invoice, Decimal("300"), "P-1"))
        invalid = payment_data(values, invoice, Decimal("100"), "P-2")
        invalid.allocations[0].amount = Decimal("50")
        with pytest.raises(AccountingError, match="equal"):
            service.create_payment(invalid)
        invoice.status = "CANCELLED"
        session.commit()
        with pytest.raises(ConflictError, match="invalid"):
            service.create_payment(payment_data(values, invoice, Decimal("10"), "P-3"))


def test_failed_payment_post_rolls_back_journal_invoice_and_payment() -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        invoice = post_invoice(service, values)
        payment = service.create_payment(payment_data(values, invoice, Decimal("100"), "ROLLBACK"))
        values.cash.is_active = False
        session.commit()
        before = len(session.scalars(select(JournalEntry)).all())
        with pytest.raises(ConflictError, match="Inactive"):
            service.post_payment(
                payment.id,
                PaymentPost(
                    cash_account_id=values.cash.id,
                    receivable_account_id=values.receivable.id,
                ),
            )
        session.refresh(payment)
        session.refresh(invoice)
        assert payment.status == "DRAFT" and payment.journal_id is None
        assert invoice.amount_paid == 0 and invoice.status == "ISSUED"
        assert len(session.scalars(select(JournalEntry)).all()) == before


def test_audits_cover_accounting_mutations_without_secrets() -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        journal = service.create_journal(journal_data(values))
        service.post_journal(journal.id)
        events = session.scalars(
            select(AuditEvent).where(AuditEvent.action.like("accounting.%"))
        ).all()
        assert {event.action for event in events} >= {
            "accounting.journal.created",
            "accounting.journal.posted",
        }
        assert "password" not in str([event.details for event in events]).casefold()


def test_master_data_period_and_hierarchy_rules() -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        with pytest.raises(AccountingError, match="customer or supplier"):
            service.create_party(PartyCreate(name="No role"))
        supplier = service.create_party(PartyCreate(name="Supplier", is_supplier=True))
        service.update_party(supplier.id, PartyUpdate(phone="555", is_customer=True))
        assert supplier.phone == "555" and supplier.is_customer
        with pytest.raises(AccountingError, match="retain"):
            service.update_party(supplier.id, PartyUpdate(is_customer=False, is_supplier=False))
        session.rollback()

        product = service.create_product(
            ProductCreate(sku="P-2", name="Other", unit_price=Decimal("1.23"))
        )
        service.update_product(product.id, ProductUpdate(unit_price=Decimal("2.34")))
        assert product.unit_price == Decimal("2.34")
        with pytest.raises(ConflictError):
            service.create_product(
                ProductCreate(sku="P-2", name="Duplicate", unit_price=Decimal("1"))
            )

        category = service.create_category(CategoryCreate(name="Expenses", account_type="EXPENSE"))
        parent = service.create_account(
            AccountCreate(code="5000", name="Expenses", category_id=category.id)
        )
        child = service.create_account(
            AccountCreate(code="5100", name="Office", category_id=category.id, parent_id=parent.id)
        )
        service.update_account(child.id, AccountUpdate(name="Office costs"))
        assert child.name == "Office costs"
        with pytest.raises(AccountingError, match="own parent"):
            service.update_account(child.id, AccountUpdate(parent_id=child.id))

        with pytest.raises(AccountingError, match="start date"):
            service.create_period(
                PeriodCreate(name="Invalid", start_date=date(2027, 2, 1), end_date=date(2027, 1, 1))
            )
        with pytest.raises(ConflictError, match="overlap"):
            service.create_period(
                PeriodCreate(name="Overlap", start_date=date(2026, 6, 1), end_date=date(2027, 1, 1))
            )
        service.close_period(values.period.id)
        assert values.period.status == "CLOSED"
        assert service.get(Product, product.id) is product
        assert product in service.list(Product)
        with pytest.raises(NotFoundError):
            service.get(Product, values.admin.id)


def test_posted_account_category_cannot_rewrite_historical_reports() -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        post_invoice(service, values)
        expense = service.create_category(
            CategoryCreate(name="Reclassification target", account_type="EXPENSE")
        )

        with pytest.raises(ConflictError, match="posted journals"):
            service.update_account(
                values.receivable.id,
                AccountUpdate(category_id=expense.id),
            )

        session.refresh(values.receivable)
        assert values.receivable.category_id != expense.id


def test_invalid_invoice_and_payment_parties_and_products() -> None:
    with SessionLocal() as session:
        service, values = domain(session)
        values.customer.is_active = False
        session.commit()
        with pytest.raises(AccountingError, match="active customer"):
            service.create_invoice(invoice_data(values))
        values.customer.is_active = True
        values.product.is_active = False
        session.commit()
        with pytest.raises(AccountingError, match="Inactive products"):
            service.create_invoice(invoice_data(values))
        values.product.is_active = True
        session.commit()
        invalid_dates = invoice_data(values)
        invalid_dates.due_date = date(2026, 1, 1)
        with pytest.raises(AccountingError, match="due date"):
            service.create_invoice(invalid_dates)


def test_party_contract_rejects_blank_names_and_invalid_email() -> None:
    with pytest.raises(ValidationError):
        PartyCreate(name="   ", is_customer=True)
    with pytest.raises(ValidationError):
        PartyCreate(name="Customer", email="not-an-email", is_customer=True)
