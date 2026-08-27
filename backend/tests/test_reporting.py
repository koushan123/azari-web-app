from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest
from backend.app.db.database import SessionLocal
from backend.app.db.models import (
    Account,
    AccountCategory,
    FinancialPeriod,
    Invoice,
    Party,
    Product,
    Role,
    User,
)
from backend.app.schemas.accounting import (
    InvoiceCreate,
    InvoiceIssue,
    JournalCreate,
    PaymentCreate,
    PaymentPost,
)
from backend.app.services.accounting import AccountingError, AccountingService
from backend.app.services.reporting import ReportingService
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass
class ReportDomain:
    actor: User
    party: Party
    invoice: Invoice
    cash: Account
    receivable: Account
    payable: Account
    equity: Account
    revenue: Account
    expense: Account


def add_journal(
    service: AccountingService,
    period: FinancialPeriod,
    number: str,
    entry_date: date,
    debit: Account,
    credit: Account,
    amount: Decimal,
    *,
    post: bool = True,
) -> None:
    journal = service.create_journal(
        JournalCreate(
            entry_number=number,
            entry_date=entry_date,
            description=number,
            period_id=period.id,
            lines=[
                {"account_id": debit.id, "debit": amount, "credit": 0},
                {"account_id": credit.id, "debit": 0, "credit": amount},
            ],
        )
    )
    if post:
        service.post_journal(journal.id)


def report_domain(session: Session) -> ReportDomain:
    admin = session.scalar(select(Role).where(Role.name == "ADMIN"))
    actor = User(
        email="reports@example.com",
        password_hash="unused",
        first_name="Report",
        last_name="User",
        roles=[admin],
    )
    categories = {
        kind: AccountCategory(name=f"Report {kind}", account_type=kind)
        for kind in ["ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"]
    }
    session.add_all([actor, *categories.values()])
    session.flush()
    cash = Account(code="R-100", name="Cash", category=categories["ASSET"])
    receivable = Account(code="R-110", name="Receivable", category=categories["ASSET"])
    payable = Account(code="R-200", name="Payable", category=categories["LIABILITY"])
    equity = Account(code="R-300", name="Capital", category=categories["EQUITY"])
    revenue = Account(code="R-400", name="Revenue", category=categories["REVENUE"])
    expense = Account(code="R-500", name="Expense", category=categories["EXPENSE"])
    period = FinancialPeriod(
        name="Report 2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)
    )
    party = Party(name="Report Customer", is_customer=True)
    product = Product(sku="R-P", name="Reporting", unit_price=Decimal("100"))
    session.add_all([cash, receivable, payable, equity, revenue, expense, period, party, product])
    session.commit()
    accounting = AccountingService(session, actor)
    add_journal(accounting, period, "R-CAPITAL", date(2026, 1, 1), cash, equity, Decimal("1000"))
    invoice = accounting.create_invoice(
        InvoiceCreate(
            invoice_number="R-I-1",
            customer_id=party.id,
            issue_date=date(2026, 2, 1),
            due_date=date(2026, 2, 15),
            items=[
                {
                    "product_id": product.id,
                    "description": "Three units",
                    "quantity": Decimal("3"),
                }
            ],
        )
    )
    accounting.issue_invoice(
        invoice.id,
        InvoiceIssue(receivable_account_id=receivable.id, revenue_account_id=revenue.id),
    )
    add_journal(accounting, period, "R-EXPENSE", date(2026, 2, 5), expense, cash, Decimal("80"))
    add_journal(accounting, period, "R-PAYABLE", date(2026, 2, 6), expense, payable, Decimal("50"))
    add_journal(
        accounting,
        period,
        "R-DRAFT",
        date(2026, 2, 7),
        receivable,
        revenue,
        Decimal("999"),
        post=False,
    )
    payment = accounting.create_payment(
        PaymentCreate(
            party_id=party.id,
            payment_date=date(2026, 2, 20),
            amount=Decimal("100"),
            reference="R-PAY-1",
            method="bank",
            allocations=[{"invoice_id": invoice.id, "amount": Decimal("100")}],
        )
    )
    accounting.post_payment(
        payment.id,
        PaymentPost(cash_account_id=cash.id, receivable_account_id=receivable.id),
    )
    return ReportDomain(actor, party, invoice, cash, receivable, payable, equity, revenue, expense)


def test_financial_statements_use_only_posted_balanced_activity() -> None:
    with SessionLocal() as session:
        values = report_domain(session)
        reports = ReportingService(session)
        trial = reports.trial_balance(end_date=date(2026, 2, 28))
        assert trial.balanced and trial.total_debit == trial.total_credit
        assert (
            next(line for line in trial.lines if line.account_id == values.revenue.id).credit == 300
        )
        income = reports.income_statement(date(2026, 2, 1), date(2026, 2, 28))
        assert income.total_revenue == Decimal("300.00")
        assert income.total_expenses == Decimal("130.00")
        assert income.net_income == Decimal("170.00")
        assert reports.account_summary("REVENUE").total == Decimal("300.00")
        assert reports.account_summary("EXPENSE").total == Decimal("130.00")
        balance = reports.balance_sheet(date(2026, 2, 28))
        assert balance.total_assets == Decimal("1220.00")
        assert balance.total_liabilities == Decimal("50.00")
        assert balance.total_equity == Decimal("1000.00")
        assert balance.current_earnings == Decimal("170.00")
        assert balance.balanced


def test_receivables_historical_as_of_filter_payables_cash_and_dashboard() -> None:
    with SessionLocal() as session:
        values = report_domain(session)
        reports = ReportingService(session)
        before_payment = reports.receivables(date(2026, 2, 16), values.party.id)
        assert before_payment.total_outstanding == Decimal("300.00")
        assert before_payment.total_overdue == Decimal("300.00")
        after_payment = reports.receivables(date(2026, 2, 28))
        assert after_payment.total_outstanding == Decimal("200.00")
        assert after_payment.lines[0].status == "OVERDUE"
        payables = reports.payables(date(2026, 2, 28))
        assert payables.total_payables == Decimal("50.00")
        assert not payables.supplier_detail_available
        cash = reports.cash_flow(date(2026, 2, 1), date(2026, 2, 28))
        assert cash.total_inflow == Decimal("100.00") and cash.net_cash_flow == Decimal("100.00")
        dashboard = reports.dashboard(
            as_of=date(2026, 2, 28), start_date=date(2026, 2, 1), end_date=date(2026, 2, 28)
        )
        assert dashboard.net_income == Decimal("170.00")
        assert dashboard.outstanding_invoices == Decimal("200.00")
        assert dashboard.overdue_invoice_count == 1


def test_draft_invoice_does_not_affect_receivables_or_dashboard() -> None:
    with SessionLocal() as session:
        values = report_domain(session)
        service = AccountingService(session, values.actor)
        service.create_invoice(
            InvoiceCreate(
                invoice_number="REPORT-DRAFT",
                customer_id=values.party.id,
                issue_date=date(2026, 2, 10),
                due_date=date(2026, 2, 15),
                items=[
                    {
                        "description": "Unissued work",
                        "quantity": Decimal("1"),
                        "unit_price": Decimal("999"),
                    }
                ],
            )
        )
        reports = ReportingService(session)

        receivables = reports.receivables(date(2026, 2, 28))
        dashboard = reports.dashboard(
            as_of=date(2026, 2, 28),
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
        )

        assert receivables.total_outstanding == Decimal("200.00")
        assert dashboard.outstanding_invoices == Decimal("200.00")


def test_party_history_filters_and_invalid_ranges() -> None:
    with SessionLocal() as session:
        values = report_domain(session)
        reports = ReportingService(session)
        history = reports.party_history(values.party.id, date(2026, 2, 1), date(2026, 2, 28))
        assert [item.kind for item in history.transactions] == ["INVOICE", "PAYMENT"]
        with pytest.raises(AccountingError, match="start_date"):
            reports.trial_balance(date(2026, 3, 1), date(2026, 2, 1))
        with pytest.raises(AccountingError, match="start_date"):
            reports.cash_flow(date(2026, 3, 1), date(2026, 2, 1))
