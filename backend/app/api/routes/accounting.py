from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_permission
from backend.app.db.database import get_db
from backend.app.db.models import (
    Account,
    AccountCategory,
    Bill,
    BillPayment,
    FinancialPeriod,
    Invoice,
    JournalEntry,
    Party,
    Payment,
    Product,
    User,
)
from backend.app.schemas.accounting import (
    AccountCreate,
    AccountRead,
    AccountUpdate,
    BillCreate,
    BillIssue,
    BillPaymentCreate,
    BillPaymentPost,
    BillPaymentRead,
    BillRead,
    CategoryCreate,
    CategoryRead,
    InvoiceCreate,
    InvoiceIssue,
    InvoiceRead,
    JournalCreate,
    JournalRead,
    PartyCreate,
    PartyRead,
    PartyUpdate,
    PaymentCreate,
    PaymentPost,
    PaymentRead,
    PeriodCreate,
    PeriodRead,
    ProductCreate,
    ProductRead,
    ProductUpdate,
)
from backend.app.services.accounting import AccountingService

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_db)]


def service(session: Session, actor: User) -> AccountingService:
    return AccountingService(session, actor)


@router.post("/parties", response_model=PartyRead, status_code=status.HTTP_201_CREATED)
def create_party(
    data: PartyCreate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("parties:write"))],
) -> Party:
    return service(session, actor).create_party(data)


@router.get("/parties", response_model=list[PartyRead])
def list_parties(
    session: SessionDep, actor: Annotated[User, Depends(require_permission("parties:read"))]
) -> list[object]:
    return service(session, actor).list(Party)


@router.get("/parties/{item_id}", response_model=PartyRead)
def get_party(
    item_id: UUID,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("parties:read"))],
) -> object:
    return service(session, actor).get(Party, item_id)


@router.patch("/parties/{item_id}", response_model=PartyRead)
def update_party(
    item_id: UUID,
    data: PartyUpdate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("parties:write"))],
) -> Party:
    return service(session, actor).update_party(item_id, data)


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("products:write"))],
) -> Product:
    return service(session, actor).create_product(data)


@router.get("/products", response_model=list[ProductRead])
def list_products(
    session: SessionDep, actor: Annotated[User, Depends(require_permission("products:read"))]
) -> list[object]:
    return service(session, actor).list(Product)


@router.get("/products/{item_id}", response_model=ProductRead)
def get_product(
    item_id: UUID,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("products:read"))],
) -> object:
    return service(session, actor).get(Product, item_id)


@router.patch("/products/{item_id}", response_model=ProductRead)
def update_product(
    item_id: UUID,
    data: ProductUpdate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("products:write"))],
) -> Product:
    return service(session, actor).update_product(item_id, data)


@router.post("/account-categories", response_model=CategoryRead, status_code=201)
def create_category(
    data: CategoryCreate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("accounts:write"))],
) -> AccountCategory:
    return service(session, actor).create_category(data)


@router.get("/account-categories", response_model=list[CategoryRead])
def list_categories(
    session: SessionDep, actor: Annotated[User, Depends(require_permission("accounts:read"))]
) -> list[object]:
    return service(session, actor).list(AccountCategory)


@router.post("/accounts", response_model=AccountRead, status_code=201)
def create_account(
    data: AccountCreate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("accounts:write"))],
) -> Account:
    return service(session, actor).create_account(data)


@router.get("/accounts", response_model=list[AccountRead])
def list_accounts(
    session: SessionDep, actor: Annotated[User, Depends(require_permission("accounts:read"))]
) -> list[object]:
    return service(session, actor).list(Account)


@router.get("/accounts/{item_id}", response_model=AccountRead)
def get_account(
    item_id: UUID,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("accounts:read"))],
) -> object:
    return service(session, actor).get(Account, item_id)


@router.patch("/accounts/{item_id}", response_model=AccountRead)
def update_account(
    item_id: UUID,
    data: AccountUpdate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("accounts:write"))],
) -> Account:
    return service(session, actor).update_account(item_id, data)


@router.post("/periods", response_model=PeriodRead, status_code=201)
def create_period(
    data: PeriodCreate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("periods:manage"))],
) -> FinancialPeriod:
    return service(session, actor).create_period(data)


@router.get("/periods", response_model=list[PeriodRead])
def list_periods(
    session: SessionDep, actor: Annotated[User, Depends(require_permission("periods:read"))]
) -> list[object]:
    return service(session, actor).list(FinancialPeriod)


@router.post("/periods/{item_id}/close", response_model=PeriodRead)
def close_period(
    item_id: UUID,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("periods:manage"))],
) -> FinancialPeriod:
    return service(session, actor).close_period(item_id)


@router.post("/journals", response_model=JournalRead, status_code=201)
def create_journal(
    data: JournalCreate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("journals:write"))],
) -> JournalEntry:
    return service(session, actor).create_journal(data)


@router.get("/journals", response_model=list[JournalRead])
def list_journals(
    session: SessionDep, actor: Annotated[User, Depends(require_permission("journals:read"))]
) -> list[object]:
    return service(session, actor).list(JournalEntry)


@router.get("/journals/{item_id}", response_model=JournalRead)
def get_journal(
    item_id: UUID,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("journals:read"))],
) -> object:
    return service(session, actor).get(JournalEntry, item_id)


@router.post("/journals/{item_id}/post", response_model=JournalRead)
def post_journal(
    item_id: UUID,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("journals:post"))],
) -> JournalEntry:
    return service(session, actor).post_journal(item_id)


@router.post("/journals/{item_id}/reverse", response_model=JournalRead, status_code=201)
def reverse_journal(
    item_id: UUID,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("journals:post"))],
) -> JournalEntry:
    return service(session, actor).reverse_journal(item_id)


@router.post("/invoices", response_model=InvoiceRead, status_code=201)
def create_invoice(
    data: InvoiceCreate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("invoices:write"))],
) -> Invoice:
    return service(session, actor).create_invoice(data)


@router.get("/invoices", response_model=list[InvoiceRead])
def list_invoices(
    session: SessionDep, actor: Annotated[User, Depends(require_permission("invoices:read"))]
) -> list[object]:
    return service(session, actor).list(Invoice)


@router.get("/invoices/{item_id}", response_model=InvoiceRead)
def get_invoice(
    item_id: UUID,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("invoices:read"))],
) -> object:
    return service(session, actor).get(Invoice, item_id)


@router.post("/invoices/{item_id}/issue", response_model=InvoiceRead)
def issue_invoice(
    item_id: UUID,
    data: InvoiceIssue,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("invoices:issue"))],
) -> Invoice:
    return service(session, actor).issue_invoice(item_id, data)


@router.post("/payments", response_model=PaymentRead, status_code=201)
def create_payment(
    data: PaymentCreate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("payments:write"))],
) -> Payment:
    return service(session, actor).create_payment(data)


@router.get("/payments", response_model=list[PaymentRead])
def list_payments(
    session: SessionDep, actor: Annotated[User, Depends(require_permission("payments:read"))]
) -> list[object]:
    return service(session, actor).list(Payment)


@router.get("/payments/{item_id}", response_model=PaymentRead)
def get_payment(
    item_id: UUID,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("payments:read"))],
) -> object:
    return service(session, actor).get(Payment, item_id)


@router.post("/payments/{item_id}/post", response_model=PaymentRead)
def post_payment(
    item_id: UUID,
    data: PaymentPost,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("payments:post"))],
) -> Payment:
    return service(session, actor).post_payment(item_id, data)


@router.post("/bills", response_model=BillRead, status_code=201)
def create_bill(
    data: BillCreate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("bills:write"))],
) -> Bill:
    return service(session, actor).create_bill(data)


@router.get("/bills", response_model=list[BillRead])
def list_bills(
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("bills:read"))],
) -> list[object]:
    return service(session, actor).list(Bill)


@router.get("/bills/{item_id}", response_model=BillRead)
def get_bill(
    item_id: UUID,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("bills:read"))],
) -> object:
    return service(session, actor).get(Bill, item_id)


@router.post("/bills/{item_id}/issue", response_model=BillRead)
def issue_bill(
    item_id: UUID,
    data: BillIssue,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("bills:issue"))],
) -> Bill:
    return service(session, actor).issue_bill(item_id, data)


@router.post("/bill-payments", response_model=BillPaymentRead, status_code=201)
def create_bill_payment(
    data: BillPaymentCreate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("bill_payments:write"))],
) -> BillPayment:
    return service(session, actor).create_bill_payment(data)


@router.get("/bill-payments", response_model=list[BillPaymentRead])
def list_bill_payments(
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("bill_payments:read"))],
) -> list[object]:
    return service(session, actor).list(BillPayment)


@router.get("/bill-payments/{item_id}", response_model=BillPaymentRead)
def get_bill_payment(
    item_id: UUID,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("bill_payments:read"))],
) -> object:
    return service(session, actor).get(BillPayment, item_id)


@router.post("/bill-payments/{item_id}/post", response_model=BillPaymentRead)
def post_bill_payment(
    item_id: UUID,
    data: BillPaymentPost,
    session: SessionDep,
    actor: Annotated[User, Depends(require_permission("bill_payments:post"))],
) -> BillPayment:
    return service(session, actor).post_bill_payment(item_id, data)
