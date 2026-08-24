from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_permission
from backend.app.db.database import get_db
from backend.app.db.models import User
from backend.app.schemas.reporting import (
    AccountSummaryReport,
    BalanceSheetReport,
    CashFlowReport,
    DashboardReport,
    IncomeStatementReport,
    PartyHistoryReport,
    PayableExposureReport,
    ReceivablesReport,
    TrialBalanceReport,
)
from backend.app.services.reporting import ReportingService

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_db)]
ReportReader = Annotated[User, Depends(require_permission("reports:read"))]


@router.get("/reports/trial-balance", response_model=TrialBalanceReport)
def trial_balance(
    session: SessionDep,
    _: ReportReader,
    start_date: date | None = None,
    end_date: date | None = None,
) -> TrialBalanceReport:
    return ReportingService(session).trial_balance(start_date, end_date)


@router.get("/reports/income-statement", response_model=IncomeStatementReport)
def income_statement(
    session: SessionDep,
    _: ReportReader,
    start_date: date | None = None,
    end_date: date | None = None,
) -> IncomeStatementReport:
    return ReportingService(session).income_statement(start_date, end_date)


@router.get("/reports/revenue", response_model=AccountSummaryReport)
def revenue_report(
    session: SessionDep,
    _: ReportReader,
    start_date: date | None = None,
    end_date: date | None = None,
) -> AccountSummaryReport:
    return ReportingService(session).account_summary("REVENUE", start_date, end_date)


@router.get("/reports/expenses", response_model=AccountSummaryReport)
def expense_report(
    session: SessionDep,
    _: ReportReader,
    start_date: date | None = None,
    end_date: date | None = None,
) -> AccountSummaryReport:
    return ReportingService(session).account_summary("EXPENSE", start_date, end_date)


@router.get("/reports/balance-sheet", response_model=BalanceSheetReport)
def balance_sheet(
    session: SessionDep,
    _: ReportReader,
    as_of: date | None = None,
) -> BalanceSheetReport:
    return ReportingService(session).balance_sheet(as_of or date.today())


@router.get("/reports/receivables", response_model=ReceivablesReport)
def receivables(
    session: SessionDep,
    _: ReportReader,
    as_of: date | None = None,
    customer_id: UUID | None = None,
) -> ReceivablesReport:
    return ReportingService(session).receivables(as_of or date.today(), customer_id)


@router.get("/reports/payables", response_model=PayableExposureReport)
def payables(
    session: SessionDep,
    _: ReportReader,
    as_of: date | None = None,
) -> PayableExposureReport:
    return ReportingService(session).payables(as_of or date.today())


@router.get("/reports/cash-flow", response_model=CashFlowReport)
def cash_flow(
    session: SessionDep,
    _: ReportReader,
    start_date: date | None = None,
    end_date: date | None = None,
) -> CashFlowReport:
    return ReportingService(session).cash_flow(start_date, end_date)


@router.get("/reports/parties/{party_id}/history", response_model=PartyHistoryReport)
def party_history(
    party_id: UUID,
    session: SessionDep,
    _: ReportReader,
    start_date: date | None = None,
    end_date: date | None = None,
) -> PartyHistoryReport:
    return ReportingService(session).party_history(party_id, start_date, end_date)


@router.get("/dashboard", response_model=DashboardReport)
def dashboard(
    session: SessionDep,
    _: ReportReader,
    as_of: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> DashboardReport:
    return ReportingService(session).dashboard(
        as_of=as_of or date.today(), start_date=start_date, end_date=end_date
    )
