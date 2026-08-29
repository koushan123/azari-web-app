from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from backend.app.db.models import (
    Account,
    AccountCategory,
    Bill,
    BillPayment,
    BillPaymentAllocation,
    Invoice,
    JournalEntry,
    JournalLine,
    Party,
    Payment,
    PaymentAllocation,
)


class ReportingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def account_activity(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        account_types: set[str] | None = None,
    ) -> list[tuple[Account, str, Decimal, Decimal]]:
        statement = (
            select(
                Account,
                AccountCategory.account_type,
                func.coalesce(func.sum(JournalLine.debit), 0),
                func.coalesce(func.sum(JournalLine.credit), 0),
            )
            .join(Account.category)
            .join(JournalLine, JournalLine.account_id == Account.id)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
            .where(JournalEntry.status == "POSTED")
            .group_by(Account.id, AccountCategory.account_type)
            .order_by(Account.code)
        )
        if start_date is not None:
            statement = statement.where(JournalEntry.entry_date >= start_date)
        if end_date is not None:
            statement = statement.where(JournalEntry.entry_date <= end_date)
        if account_types:
            statement = statement.where(AccountCategory.account_type.in_(account_types))
        return [
            (row[0], row[1], Decimal(row[2]), Decimal(row[3]))
            for row in self.session.execute(statement)
        ]

    def receivables_as_of(
        self, *, as_of: date, customer_id: UUID | None = None
    ) -> list[tuple[Invoice, Decimal]]:
        paid = func.coalesce(
            func.sum(
                case(
                    (
                        (Payment.status == "POSTED") & (Payment.payment_date <= as_of),
                        PaymentAllocation.amount,
                    ),
                    else_=0,
                )
            ),
            0,
        )
        statement = (
            select(Invoice, paid.label("paid_as_of"))
            .outerjoin(PaymentAllocation, PaymentAllocation.invoice_id == Invoice.id)
            .outerjoin(Payment, Payment.id == PaymentAllocation.payment_id)
            .where(
                Invoice.issue_date <= as_of,
                Invoice.status.in_(("ISSUED", "PARTIALLY_PAID", "PAID")),
            )
            .group_by(Invoice.id)
            .having(Invoice.total > paid)
            .order_by(Invoice.due_date, Invoice.invoice_number)
        )
        if customer_id is not None:
            statement = statement.where(Invoice.customer_id == customer_id)
        return [(row[0], Decimal(row[1])) for row in self.session.execute(statement)]

    def payables_as_of(self, *, as_of: date) -> list[tuple[Bill, Decimal]]:
        paid = func.coalesce(
            func.sum(
                case(
                    (
                        (BillPayment.status == "POSTED")
                        & (BillPayment.payment_date <= as_of),
                        BillPaymentAllocation.amount,
                    ),
                    else_=0,
                )
            ),
            0,
        )
        statement = (
            select(Bill, paid.label("paid_as_of"))
            .outerjoin(BillPaymentAllocation, BillPaymentAllocation.bill_id == Bill.id)
            .outerjoin(BillPayment, BillPayment.id == BillPaymentAllocation.bill_payment_id)
            .where(
                Bill.issue_date <= as_of,
                Bill.status.in_(("ISSUED", "PARTIALLY_PAID", "PAID")),
            )
            .group_by(Bill.id)
            .having(Bill.total > paid)
            .order_by(Bill.due_date, Bill.bill_number)
        )
        return [(row[0], Decimal(row[1])) for row in self.session.execute(statement)]

    def party(self, party_id: UUID) -> Party | None:
        return self.session.get(Party, party_id)

    def party_invoices(
        self, party_id: UUID, start_date: date | None, end_date: date | None
    ) -> list[Invoice]:
        statement = select(Invoice).where(Invoice.customer_id == party_id)
        if start_date is not None:
            statement = statement.where(Invoice.issue_date >= start_date)
        if end_date is not None:
            statement = statement.where(Invoice.issue_date <= end_date)
        return list(self.session.scalars(statement))

    def party_payments(
        self, party_id: UUID, start_date: date | None, end_date: date | None
    ) -> list[Payment]:
        statement = select(Payment).where(Payment.party_id == party_id)
        if start_date is not None:
            statement = statement.where(Payment.payment_date >= start_date)
        if end_date is not None:
            statement = statement.where(Payment.payment_date <= end_date)
        return list(self.session.scalars(statement))

    def posted_payments(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[Payment]:
        statement = select(Payment).where(Payment.status == "POSTED")
        if start_date is not None:
            statement = statement.where(Payment.payment_date >= start_date)
        if end_date is not None:
            statement = statement.where(Payment.payment_date <= end_date)
        return list(self.session.scalars(statement))

    def posted_bill_payments(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[BillPayment]:
        statement = select(BillPayment).where(BillPayment.status == "POSTED")
        if start_date is not None:
            statement = statement.where(BillPayment.payment_date >= start_date)
        if end_date is not None:
            statement = statement.where(BillPayment.payment_date <= end_date)
        return list(self.session.scalars(statement))
