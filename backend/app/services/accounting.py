from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.base import Base
from backend.app.db.models import (
    Account,
    AccountCategory,
    FinancialPeriod,
    Invoice,
    InvoiceItem,
    JournalEntry,
    JournalLine,
    Party,
    Payment,
    PaymentAllocation,
    Product,
    User,
)
from backend.app.repositories.accounting import AccountingRepository
from backend.app.repositories.audit import AuditRepository
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

CENT = Decimal("0.01")
ModelT = TypeVar("ModelT", bound=Base)


class AccountingError(ValueError):
    pass


class NotFoundError(AccountingError):
    pass


class ConflictError(AccountingError):
    pass


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


class AccountingService:
    def __init__(self, session: Session, actor: User) -> None:
        self.session = session
        self.actor = actor
        self.repo = AccountingRepository(session)
        self.audit = AuditRepository(session)

    def _commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("A unique or database constraint was violated") from exc

    def _flush(self) -> None:
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("A unique or database constraint was violated") from exc

    def _get(self, model: type[ModelT], item_id: UUID) -> ModelT:
        item = self.session.get(model, item_id)
        if item is None:
            raise NotFoundError(f"{model.__name__} not found")
        return item

    def _audit(self, action: str, resource: Base) -> None:
        self.audit.record(
            action=action,
            resource_type=type(resource).__name__.casefold(),
            resource_id=str(resource.id),  # type: ignore[attr-defined]
            actor_id=self.actor.id,
            success=True,
        )

    def create_party(self, data: PartyCreate) -> Party:
        if not data.is_customer and not data.is_supplier:
            raise AccountingError("A party must be a customer or supplier")
        party = Party(**data.model_dump())
        self.session.add(party)
        self._flush()
        self._audit("accounting.party.created", party)
        self._commit()
        return party

    def update_party(self, party_id: UUID, data: PartyUpdate) -> Party:
        party = self._get(Party, party_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(party, key, value)
        if not party.is_customer and not party.is_supplier:
            raise AccountingError("A party must retain at least one role")
        self._audit("accounting.party.updated", party)
        self._commit()
        return party

    def create_product(self, data: ProductCreate) -> Product:
        product = Product(**data.model_dump())
        self.session.add(product)
        self._flush()
        self._audit("accounting.product.created", product)
        self._commit()
        return product

    def update_product(self, product_id: UUID, data: ProductUpdate) -> Product:
        product = self._get(Product, product_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(product, key, value)
        self._audit("accounting.product.updated", product)
        self._commit()
        return product

    def create_category(self, data: CategoryCreate) -> AccountCategory:
        category = AccountCategory(**data.model_dump())
        self.session.add(category)
        self._commit()
        return category

    def create_account(self, data: AccountCreate) -> Account:
        self._get(AccountCategory, data.category_id)
        if data.parent_id is not None:
            self._get(Account, data.parent_id)
        account = Account(**data.model_dump())
        self.session.add(account)
        self._flush()
        self._audit("accounting.account.created", account)
        self._commit()
        return account

    def update_account(self, account_id: UUID, data: AccountUpdate) -> Account:
        account = self._get(Account, account_id)
        values = data.model_dump(exclude_unset=True)
        parent_id = values.get("parent_id")
        if parent_id == account.id:
            raise AccountingError("An account cannot be its own parent")
        if parent_id is not None:
            parent: Account | None = self._get(Account, parent_id)
            seen = {account.id}
            while parent is not None:
                if parent.id in seen:
                    raise AccountingError("Circular account hierarchy")
                seen.add(parent.id)
                parent = parent.parent
        for key, value in values.items():
            setattr(account, key, value)
        self._audit("accounting.account.updated", account)
        self._commit()
        return account

    def create_period(self, data: PeriodCreate) -> FinancialPeriod:
        if data.start_date > data.end_date:
            raise AccountingError("Period start date must not exceed end date")
        overlap = self.session.scalar(
            select(FinancialPeriod).where(
                FinancialPeriod.start_date <= data.end_date,
                FinancialPeriod.end_date >= data.start_date,
            )
        )
        if overlap is not None:
            raise ConflictError("Financial periods cannot overlap")
        period = FinancialPeriod(**data.model_dump())
        self.session.add(period)
        self._flush()
        self._audit("accounting.period.created", period)
        self._commit()
        return period

    def close_period(self, period_id: UUID) -> FinancialPeriod:
        period = self._get(FinancialPeriod, period_id)
        period.status = "CLOSED"
        self._audit("accounting.period.closed", period)
        self._commit()
        return period

    @staticmethod
    def _validate_line(debit: Decimal, credit: Decimal) -> None:
        if debit < 0 or credit < 0:
            raise AccountingError("Journal amounts cannot be negative")
        if (debit > 0) == (credit > 0):
            raise AccountingError("Each line requires a positive amount on exactly one side")

    def create_journal(self, data: JournalCreate, *, commit: bool = True) -> JournalEntry:
        period = self._get(FinancialPeriod, data.period_id)
        if not period.start_date <= data.entry_date <= period.end_date:
            raise AccountingError("Journal date is outside the financial period")
        lines: list[JournalLine] = []
        for value in data.lines:
            self._validate_line(value.debit, value.credit)
            self._get(Account, value.account_id)
            lines.append(JournalLine(**value.model_dump()))
        journal = JournalEntry(
            entry_number=data.entry_number,
            entry_date=data.entry_date,
            description=data.description,
            period_id=data.period_id,
            created_by_id=self.actor.id,
            lines=lines,
        )
        self.session.add(journal)
        self._flush()
        self._audit("accounting.journal.created", journal)
        if commit:
            self._commit()
        return journal

    def _post_journal(self, journal: JournalEntry) -> JournalEntry:
        if journal.status != "DRAFT":
            raise ConflictError("Only draft journals can be posted")
        if journal.period.status != "OPEN":
            raise ConflictError("Cannot post into a closed period")
        if len(journal.lines) < 2:
            raise AccountingError("A posted journal requires at least two lines")
        debit = Decimal("0")
        credit = Decimal("0")
        for line in journal.lines:
            self._validate_line(line.debit, line.credit)
            if not line.account.is_active:
                raise ConflictError("Inactive accounts cannot receive postings")
            debit += line.debit
            credit += line.credit
        if money(debit) != money(credit):
            raise AccountingError("Journal debits and credits must balance")
        journal.status = "POSTED"
        self._audit("accounting.journal.posted", journal)
        return journal

    def post_journal(self, journal_id: UUID) -> JournalEntry:
        journal = self._get(JournalEntry, journal_id)
        try:
            self._post_journal(journal)
            self._commit()
        except Exception:
            self.session.rollback()
            raise
        return journal

    def reverse_journal(self, journal_id: UUID) -> JournalEntry:
        original = self._get(JournalEntry, journal_id)
        if original.status != "POSTED":
            raise ConflictError("Only posted journals can be reversed")
        reversal = JournalEntry(
            entry_number=f"REV-{original.entry_number}",
            entry_date=original.entry_date,
            description=f"Reversal of {original.entry_number}: {original.description}",
            period_id=original.period_id,
            created_by_id=self.actor.id,
            reversal_of_id=original.id,
            lines=[
                JournalLine(
                    account_id=line.account_id,
                    description=line.description,
                    debit=line.credit,
                    credit=line.debit,
                )
                for line in original.lines
            ],
        )
        self.session.add(reversal)
        self._flush()
        self._post_journal(reversal)
        self._audit("accounting.journal.reversed", reversal)
        self._commit()
        return reversal

    def create_invoice(self, data: InvoiceCreate) -> Invoice:
        customer = self._get(Party, data.customer_id)
        if not customer.is_customer or not customer.is_active:
            raise AccountingError("Invoice party must be an active customer")
        if data.issue_date > data.due_date:
            raise AccountingError("Invoice due date cannot precede issue date")
        items: list[InvoiceItem] = []
        subtotal = Decimal("0")
        tax_total = Decimal("0")
        for value in data.items:
            product = self._get(Product, value.product_id) if value.product_id else None
            if product is not None and not product.is_active:
                raise AccountingError("Inactive products cannot be invoiced")
            unit_price = (
                value.unit_price
                if value.unit_price is not None
                else product.unit_price
                if product
                else None
            )
            if unit_price is None:
                raise AccountingError("Unit price is required without a product")
            line_subtotal = money(value.quantity * unit_price)
            line_total = money(line_subtotal + value.tax)
            subtotal += line_subtotal
            tax_total += value.tax
            items.append(
                InvoiceItem(
                    **value.model_dump(exclude={"unit_price"}),
                    unit_price=unit_price,
                    line_subtotal=line_subtotal,
                    line_total=line_total,
                )
            )
        invoice = Invoice(
            invoice_number=data.invoice_number,
            customer_id=data.customer_id,
            issue_date=data.issue_date,
            due_date=data.due_date,
            subtotal=money(subtotal),
            tax=money(tax_total),
            total=money(subtotal + tax_total),
            items=items,
        )
        self.session.add(invoice)
        self._flush()
        self._audit("accounting.invoice.created", invoice)
        self._commit()
        return invoice

    def issue_invoice(self, invoice_id: UUID, data: InvoiceIssue) -> Invoice:
        invoice = self._get(Invoice, invoice_id)
        if invoice.status != "DRAFT":
            raise ConflictError("Only draft invoices can be issued")
        period = self._period_for(invoice.issue_date)
        journal = self.create_journal(
            JournalCreate(
                entry_number=f"INV-{invoice.invoice_number}",
                entry_date=invoice.issue_date,
                description=f"Invoice {invoice.invoice_number}",
                period_id=period.id,
                lines=[
                    {"account_id": data.receivable_account_id, "debit": invoice.total, "credit": 0},
                    {"account_id": data.revenue_account_id, "debit": 0, "credit": invoice.total},
                ],
            ),
            commit=False,
        )
        try:
            self._post_journal(journal)
            invoice.status = "ISSUED"
            invoice.journal = journal
            self._audit("accounting.invoice.issued", invoice)
            self._commit()
        except Exception:
            self.session.rollback()
            raise
        return invoice

    def _period_for(self, value: date) -> FinancialPeriod:
        period = self.session.scalar(
            select(FinancialPeriod).where(
                FinancialPeriod.start_date <= value,
                FinancialPeriod.end_date >= value,
            )
        )
        if period is None:
            raise AccountingError("No financial period contains this date")
        return period

    def create_payment(self, data: PaymentCreate) -> Payment:
        party = self._get(Party, data.party_id)
        if not party.is_customer or not party.is_active:
            raise AccountingError("Payment party must be an active customer")
        if money(sum((item.amount for item in data.allocations), Decimal("0"))) != money(
            data.amount
        ):
            raise AccountingError("Payment allocations must equal the payment amount")
        seen: set[UUID] = set()
        allocations: list[PaymentAllocation] = []
        for value in data.allocations:
            if value.invoice_id in seen:
                raise AccountingError("An invoice may be allocated only once per payment")
            seen.add(value.invoice_id)
            invoice = self._get(Invoice, value.invoice_id)
            if invoice.customer_id != party.id or invoice.status not in {
                "ISSUED",
                "PARTIALLY_PAID",
            }:
                raise ConflictError("Payment allocation targets an invalid invoice")
            if value.amount > invoice.balance_due:
                raise AccountingError("Allocation exceeds invoice balance")
            allocations.append(PaymentAllocation(**value.model_dump()))
        payment = Payment(**data.model_dump(exclude={"allocations"}), allocations=allocations)
        self.session.add(payment)
        self._flush()
        self._audit("accounting.payment.created", payment)
        self._commit()
        return payment

    def post_payment(self, payment_id: UUID, data: PaymentPost) -> Payment:
        payment = self._get(Payment, payment_id)
        if payment.status != "DRAFT":
            raise ConflictError("Only draft payments can be posted")
        period = self._period_for(payment.payment_date)
        journal = self.create_journal(
            JournalCreate(
                entry_number=f"PAY-{payment.reference}",
                entry_date=payment.payment_date,
                description=f"Payment {payment.reference}",
                period_id=period.id,
                lines=[
                    {"account_id": data.cash_account_id, "debit": payment.amount, "credit": 0},
                    {
                        "account_id": data.receivable_account_id,
                        "debit": 0,
                        "credit": payment.amount,
                    },
                ],
            ),
            commit=False,
        )
        try:
            self._post_journal(journal)
            for allocation in payment.allocations:
                invoice = allocation.invoice
                if allocation.amount > invoice.balance_due:
                    raise AccountingError("Allocation exceeds current invoice balance")
                invoice.amount_paid = money(invoice.amount_paid + allocation.amount)
                invoice.status = "PAID" if invoice.balance_due == 0 else "PARTIALLY_PAID"
            payment.status = "POSTED"
            payment.journal = journal
            self._audit("accounting.payment.posted", payment)
            self._commit()
        except Exception:
            self.session.rollback()
            raise
        return payment

    def list(
        self,
        model: type[Account]
        | type[AccountCategory]
        | type[FinancialPeriod]
        | type[Invoice]
        | type[JournalEntry]
        | type[Party]
        | type[Payment]
        | type[Product],
    ) -> list[object]:
        return list(self.session.scalars(select(model)))

    def get(
        self,
        model: type[Account]
        | type[AccountCategory]
        | type[FinancialPeriod]
        | type[Invoice]
        | type[JournalEntry]
        | type[Party]
        | type[Payment]
        | type[Product],
        item_id: UUID,
    ) -> object:
        return self._get(model, item_id)
