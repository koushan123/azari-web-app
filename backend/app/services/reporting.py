from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.db.models import Account
from backend.app.repositories.reporting import ReportingRepository
from backend.app.schemas.reporting import (
    AccountReportLine,
    AccountSummaryReport,
    BalanceSheetReport,
    CashFlowPoint,
    CashFlowReport,
    DashboardReport,
    IncomeStatementReport,
    PartyHistoryReport,
    PartyTransaction,
    PayableExposureReport,
    PayableLine,
    ReceivableLine,
    ReceivablesReport,
    TrialBalanceReport,
)
from backend.app.services.accounting import AccountingError, NotFoundError, money

ZERO = Decimal("0.00")


class ReportingService:
    def __init__(self, session: Session) -> None:
        self.repo = ReportingRepository(session)

    @staticmethod
    def _validate_range(start_date: date | None, end_date: date | None) -> None:
        if start_date is not None and end_date is not None and start_date > end_date:
            raise AccountingError("start_date must not exceed end_date")

    @staticmethod
    def _line(
        account: Account, account_type: str, debit: Decimal, credit: Decimal
    ) -> AccountReportLine:
        normal_debit = account_type in {"ASSET", "EXPENSE"}
        balance = debit - credit if normal_debit else credit - debit
        return AccountReportLine(
            account_id=account.id,
            code=account.code,
            name=account.name,
            account_type=account_type,
            debit=money(debit),
            credit=money(credit),
            balance=money(balance),
        )

    def _activity(
        self,
        start_date: date | None,
        end_date: date | None,
        account_types: set[str] | None = None,
    ) -> list[AccountReportLine]:
        self._validate_range(start_date, end_date)
        return [
            self._line(account, account_type, debit, credit)
            for account, account_type, debit, credit in self.repo.account_activity(
                start_date=start_date, end_date=end_date, account_types=account_types
            )
        ]

    def trial_balance(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> TrialBalanceReport:
        lines = self._activity(start_date, end_date)
        total_debit = money(sum((line.debit for line in lines), ZERO))
        total_credit = money(sum((line.credit for line in lines), ZERO))
        return TrialBalanceReport(
            start_date=start_date,
            end_date=end_date,
            lines=lines,
            total_debit=total_debit,
            total_credit=total_credit,
            balanced=total_debit == total_credit,
        )

    def income_statement(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> IncomeStatementReport:
        lines = self._activity(start_date, end_date, {"REVENUE", "EXPENSE"})
        revenue = [line for line in lines if line.account_type == "REVENUE"]
        expenses = [line for line in lines if line.account_type == "EXPENSE"]
        total_revenue = money(sum((line.balance for line in revenue), ZERO))
        total_expenses = money(sum((line.balance for line in expenses), ZERO))
        return IncomeStatementReport(
            start_date=start_date,
            end_date=end_date,
            revenue=revenue,
            expenses=expenses,
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            net_income=money(total_revenue - total_expenses),
        )

    def account_summary(
        self,
        account_type: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> AccountSummaryReport:
        lines = self._activity(start_date, end_date, {account_type})
        return AccountSummaryReport(
            start_date=start_date,
            end_date=end_date,
            account_type=account_type,
            lines=lines,
            total=money(sum((line.balance for line in lines), ZERO)),
        )

    def balance_sheet(self, as_of: date) -> BalanceSheetReport:
        lines = self._activity(None, as_of)
        assets = [line for line in lines if line.account_type == "ASSET"]
        liabilities = [line for line in lines if line.account_type == "LIABILITY"]
        equity = [line for line in lines if line.account_type == "EQUITY"]
        revenue = sum((line.balance for line in lines if line.account_type == "REVENUE"), ZERO)
        expenses = sum((line.balance for line in lines if line.account_type == "EXPENSE"), ZERO)
        total_assets = money(sum((line.balance for line in assets), ZERO))
        total_liabilities = money(sum((line.balance for line in liabilities), ZERO))
        total_equity = money(sum((line.balance for line in equity), ZERO))
        current_earnings = money(revenue - expenses)
        right_side = money(total_liabilities + total_equity + current_earnings)
        return BalanceSheetReport(
            as_of=as_of,
            assets=assets,
            liabilities=liabilities,
            equity=equity,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            total_equity=total_equity,
            current_earnings=current_earnings,
            total_liabilities_and_equity=right_side,
            balanced=total_assets == right_side,
        )

    def receivables(self, as_of: date, customer_id: UUID | None = None) -> ReceivablesReport:
        rows = self.repo.receivables_as_of(as_of=as_of, customer_id=customer_id)
        lines: list[ReceivableLine] = []
        for invoice, paid in rows:
            balance = money(invoice.total - paid)
            overdue_days = max((as_of - invoice.due_date).days, 0)
            status = "OVERDUE" if overdue_days else "PARTIALLY_PAID" if paid else "ISSUED"
            lines.append(
                ReceivableLine(
                    invoice_id=invoice.id,
                    invoice_number=invoice.invoice_number,
                    customer_id=invoice.customer_id,
                    customer_name=invoice.customer.name,
                    issue_date=invoice.issue_date,
                    due_date=invoice.due_date,
                    status=status,
                    total=invoice.total,
                    amount_paid=money(paid),
                    balance_due=balance,
                    days_overdue=overdue_days,
                )
            )
        return ReceivablesReport(
            as_of=as_of,
            customer_id=customer_id,
            lines=lines,
            total_outstanding=money(sum((line.balance_due for line in lines), ZERO)),
            total_overdue=money(
                sum((line.balance_due for line in lines if line.days_overdue > 0), ZERO)
            ),
        )

    def payables(self, as_of: date) -> PayableExposureReport:
        lines: list[PayableLine] = []
        for bill, paid in self.repo.payables_as_of(as_of=as_of):
            balance = money(bill.total - paid)
            overdue_days = max((as_of - bill.due_date).days, 0)
            status = "OVERDUE" if overdue_days else "PARTIALLY_PAID" if paid else "ISSUED"
            lines.append(
                PayableLine(
                    bill_id=bill.id,
                    bill_number=bill.bill_number,
                    supplier_id=bill.supplier_id,
                    supplier_name=bill.supplier.name,
                    issue_date=bill.issue_date,
                    due_date=bill.due_date,
                    status=status,
                    total=bill.total,
                    amount_paid=money(paid),
                    balance_due=balance,
                    days_overdue=overdue_days,
                )
            )
        return PayableExposureReport(
            as_of=as_of,
            lines=lines,
            total_payables=money(sum((line.balance_due for line in lines), ZERO)),
        )

    def cash_flow(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> CashFlowReport:
        self._validate_range(start_date, end_date)
        inflows: dict[date, Decimal] = defaultdict(lambda: ZERO)
        outflows: dict[date, Decimal] = defaultdict(lambda: ZERO)
        for receipt in self.repo.posted_payments(start_date, end_date):
            inflows[receipt.payment_date] += receipt.amount
        for disbursement in self.repo.posted_bill_payments(start_date, end_date):
            outflows[disbursement.payment_date] += disbursement.amount
        points = [
            CashFlowPoint(
                date=value,
                inflow=money(inflows[value]),
                outflow=money(outflows[value]),
                net=money(inflows[value] - outflows[value]),
            )
            for value in sorted(inflows.keys() | outflows.keys())
        ]
        total_inflow = money(sum((point.inflow for point in points), ZERO))
        total_outflow = money(sum((point.outflow for point in points), ZERO))
        return CashFlowReport(
            start_date=start_date,
            end_date=end_date,
            points=points,
            total_inflow=total_inflow,
            total_outflow=total_outflow,
            net_cash_flow=money(total_inflow - total_outflow),
        )

    def party_history(
        self,
        party_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> PartyHistoryReport:
        self._validate_range(start_date, end_date)
        party = self.repo.party(party_id)
        if party is None:
            raise NotFoundError("Party not found")
        transactions = [
            PartyTransaction(
                kind="INVOICE",
                record_id=item.id,
                reference=item.invoice_number,
                date=item.issue_date,
                amount=item.total,
                status=item.status,
            )
            for item in self.repo.party_invoices(party_id, start_date, end_date)
        ]
        transactions.extend(
            PartyTransaction(
                kind="PAYMENT",
                record_id=item.id,
                reference=item.reference,
                date=item.payment_date,
                amount=item.amount,
                status=item.status,
            )
            for item in self.repo.party_payments(party_id, start_date, end_date)
        )
        transactions.sort(key=lambda item: (item.date, item.kind, item.reference))
        return PartyHistoryReport(
            party_id=party.id,
            party_name=party.name,
            start_date=start_date,
            end_date=end_date,
            transactions=transactions,
        )

    def dashboard(
        self,
        *,
        as_of: date,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> DashboardReport:
        income = self.income_statement(start_date, end_date)
        cash = self.cash_flow(start_date, end_date)
        receivables = self.receivables(as_of)
        overdue = [line for line in receivables.lines if line.days_overdue > 0]
        return DashboardReport(
            start_date=start_date,
            end_date=end_date,
            as_of=as_of,
            total_revenue=income.total_revenue,
            total_expenses=income.total_expenses,
            net_income=income.net_income,
            net_cash_flow=cash.net_cash_flow,
            outstanding_invoices=receivables.total_outstanding,
            overdue_invoices=receivables.total_overdue,
            outstanding_invoice_count=len(receivables.lines),
            overdue_invoice_count=len(overdue),
        )
