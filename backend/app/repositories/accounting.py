from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class AccountingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, model: type[ModelT], item_id: UUID) -> ModelT | None:
        return self.session.get(model, item_id)

    def list(self, model: type[ModelT]) -> list[ModelT]:
        return list(self.session.scalars(select(model).order_by(model.created_at)))  # type: ignore[attr-defined]

    def add(self, item: ModelT) -> ModelT:
        self.session.add(item)
        return item
