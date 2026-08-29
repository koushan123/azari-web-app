from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class AccountReportLine(BaseModel):
    account_id: UUID
    code: str
    name: str
    account_type: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


class TrialBalanceReport(BaseModel):
    start_date: date | None
    end_date: date | None
    lines: list[AccountReportLine]
    total_debit: Decimal
    total_credit: Decimal
    balanced: bool


class IncomeStatementReport(BaseModel):
    start_date: date | None
    end_date: date | None
    revenue: list[AccountReportLine]
    expenses: list[AccountReportLine]
    total_revenue: Decimal
    total_expenses: Decimal
    net_income: Decimal


class AccountSummaryReport(BaseModel):
    start_date: date | None
    end_date: date | None
    account_type: str
    lines: list[AccountReportLine]
    total: Decimal


class BalanceSheetReport(BaseModel):
    as_of: date
    assets: list[AccountReportLine]
    liabilities: list[AccountReportLine]
    equity: list[AccountReportLine]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    current_earnings: Decimal
    total_liabilities_and_equity: Decimal
    balanced: bool


class ReceivableLine(BaseModel):
    invoice_id: UUID
    invoice_number: str
    customer_id: UUID
    customer_name: str
    issue_date: date
    due_date: date
    status: str
    total: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    days_overdue: int


class ReceivablesReport(BaseModel):
    as_of: date
    customer_id: UUID | None
    lines: list[ReceivableLine]
    total_outstanding: Decimal
    total_overdue: Decimal


class PayableLine(BaseModel):
    bill_id: UUID
    bill_number: str
    supplier_id: UUID
    supplier_name: str
    issue_date: date
    due_date: date
    status: str
    total: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    days_overdue: int


class PayableExposureReport(BaseModel):
    as_of: date
    lines: list[PayableLine]
    total_payables: Decimal
    supplier_detail_available: bool = True


class CashFlowPoint(BaseModel):
    date: date
    inflow: Decimal
    outflow: Decimal
    net: Decimal


class CashFlowReport(BaseModel):
    start_date: date | None
    end_date: date | None
    points: list[CashFlowPoint]
    total_inflow: Decimal
    total_outflow: Decimal
    net_cash_flow: Decimal


class PartyTransaction(BaseModel):
    kind: str
    record_id: UUID
    reference: str
    date: date
    amount: Decimal
    status: str


class PartyHistoryReport(BaseModel):
    party_id: UUID
    party_name: str
    start_date: date | None
    end_date: date | None
    transactions: list[PartyTransaction]


class DashboardReport(BaseModel):
    start_date: date | None
    end_date: date | None
    as_of: date
    total_revenue: Decimal
    total_expenses: Decimal
    net_income: Decimal
    net_cash_flow: Decimal
    outstanding_invoices: Decimal
    overdue_invoices: Decimal
    outstanding_invoice_count: int
    overdue_invoice_count: int
