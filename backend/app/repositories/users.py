from uuid import UUID

from sqlalchemy import func, select
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

    def get_by_id_for_update(self, user_id: UUID) -> User | None:
        statement = (
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
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

    def active_admin_count(self) -> int:
        statement = (
            select(func.count(User.id.distinct()))
            .join(User.roles)
            .where(User.is_active.is_(True), Role.name == "ADMIN")
        )
        return int(self.session.scalar(statement) or 0)
