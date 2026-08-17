from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models import Role


class RoleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_name(self, name: str) -> Role | None:
        return self.session.scalar(
            select(Role).where(Role.name == name).options(selectinload(Role.permissions))
        )
