from sqlalchemy.orm import Session

from backend.app.db.models import User
from backend.app.repositories.users import UserRepository


class UserService:
    def __init__(self, session: Session) -> None:
        self.repository = UserRepository(session)

    def list_users(self) -> list[User]:
        return self.repository.list_users()
