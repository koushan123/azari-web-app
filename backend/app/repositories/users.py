from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models import Role, User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        statement = (
            select(User)
            .where(User.email == email)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return self.session.scalar(statement)

    def get_by_id(self, user_id: UUID) -> User | None:
        statement = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return self.session.scalar(statement)

    def list_users(self) -> list[User]:
        statement = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .order_by(User.email)
        )
        return list(self.session.scalars(statement).unique())

    def add(self, user: User) -> None:
        self.session.add(user)
