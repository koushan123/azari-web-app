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

    def get_admin_for_update(self) -> Role | None:
        return self.session.scalar(
            select(Role)
            .where(Role.name == "ADMIN")
            .with_for_update()
            .execution_options(populate_existing=True)
            .options(selectinload(Role.permissions))
        )

    def get_by_names(self, names: set[str]) -> list[Role]:
        if not names:
            return []
        statement = (
            select(Role)
            .where(Role.name.in_(names))
            .options(selectinload(Role.permissions))
            .order_by(Role.name)
        )
        return list(self.session.scalars(statement))
