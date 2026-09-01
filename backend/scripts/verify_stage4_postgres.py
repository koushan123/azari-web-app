"""Verify Stage 4 report aggregation on the isolated PostgreSQL database."""

from datetime import date
from decimal import Decimal

from backend.app.db.bootstrap import seed_rbac
from backend.app.db.database import SessionLocal, engine
from backend.app.db.models import Account, AccountCategory, FinancialPeriod, Role, User
from backend.app.schemas.accounting import JournalCreate
from backend.app.services.accounting import AccountingService
from backend.app.services.reporting import ReportingService
from sqlalchemy import select, text

EXPECTED_DATABASE = "azari_stage4_test"


def main() -> None:
    with engine.connect() as connection:
        database = connection.scalar(text("select current_database()"))
        if database != EXPECTED_DATABASE:
            raise RuntimeError(f"Refusing Stage 4 verification against {database!r}")
    with SessionLocal.begin() as session:
        seed_rbac(session)
    with SessionLocal() as session:
        admin = session.scalar(select(Role).where(Role.name == "ADMIN"))
        actor = User(
            email="stage4-postgres@example.com",
            password_hash="unused",
            first_name="Stage",
            last_name="Four",
            roles=[admin],
        )
        assets = AccountCategory(name="Stage4 Assets", account_type="ASSET")
        revenue_category = AccountCategory(name="Stage4 Revenue", account_type="REVENUE")
        expense_category = AccountCategory(name="Stage4 Expense", account_type="EXPENSE")
        session.add_all([actor, assets, revenue_category, expense_category])
        session.flush()
        cash = Account(code="S4-100", name="Cash", category=assets)
        revenue = Account(code="S4-400", name="Revenue", category=revenue_category)
        expense = Account(code="S4-500", name="Expense", category=expense_category)
        period = FinancialPeriod(
            name="Stage4 2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)
        )
        session.add_all([cash, revenue, expense, period])
        session.commit()
        accounting = AccountingService(session, actor)
        for number, debit, credit, amount in [
            ("S4-REV", cash, revenue, Decimal("250.25")),
            ("S4-EXP", expense, cash, Decimal("40.10")),
        ]:
            journal = accounting.create_journal(
                JournalCreate(
                    entry_number=number,
                    entry_date=date(2026, 4, 1),
                    description=number,
                    period_id=period.id,
                    lines=[
                        {"account_id": debit.id, "debit": amount, "credit": 0},
                        {"account_id": credit.id, "debit": 0, "credit": amount},
                    ],
                )
            )
            accounting.post_journal(journal.id)
        reports = ReportingService(session, actor.id)
        trial = reports.trial_balance(date(2026, 4, 1), date(2026, 4, 30))
        income = reports.income_statement(date(2026, 4, 1), date(2026, 4, 30))
        assert trial.balanced and trial.total_debit == Decimal("290.35")
        assert income.total_revenue == Decimal("250.25")
        assert income.total_expenses == Decimal("40.10")
        assert income.net_income == Decimal("210.15")
    print("Stage 4 PostgreSQL report aggregation checks passed")


if __name__ == "__main__":
    main()
