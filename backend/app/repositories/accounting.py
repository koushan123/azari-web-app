from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class AccountingRepository:
    def __init__(self, session: Session, owner_id: UUID) -> None:
        self.session = session
        self.owner_id = owner_id

    def get(self, model: type[ModelT], item_id: UUID) -> ModelT | None:
        return self.session.scalar(
            select(model).where(
                model.id == item_id,  # type: ignore[attr-defined]
                model.owner_id == self.owner_id,  # type: ignore[attr-defined]
            )
        )

    def list(self, model: type[ModelT]) -> list[ModelT]:
        return list(
            self.session.scalars(
                select(model)
                .where(model.owner_id == self.owner_id)  # type: ignore[attr-defined]
                .order_by(model.created_at)  # type: ignore[attr-defined]
            )
        )

    def add(self, item: ModelT) -> ModelT:
        self.session.add(item)
        return item
