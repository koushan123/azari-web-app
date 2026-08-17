from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.passwords import hash_password, verify_password
from backend.app.core.tokens import create_access_token
from backend.app.db.models import User
from backend.app.repositories.audit import AuditRepository
from backend.app.repositories.roles import RoleRepository
from backend.app.repositories.users import UserRepository
from backend.app.schemas.auth import LoginRequest, RegisterRequest

PUBLIC_REGISTRATION_ROLE = "VIEWER"


class DuplicateEmailError(ValueError):
    pass


class AuthenticationError(ValueError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().casefold()


class AuthenticationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.audit = AuditRepository(session)

    def register(self, data: RegisterRequest) -> User:
        email = normalize_email(str(data.email))
        if self.users.get_by_email(email) is not None:
            self.audit.record(
                action="identity.registration",
                resource_type="user",
                success=False,
                details={"email": email, "reason": "duplicate"},
            )
            self.session.commit()
            raise DuplicateEmailError("An account with this email already exists")

        default_role = self.roles.get_by_name(PUBLIC_REGISTRATION_ROLE)
        if default_role is None:
            raise RuntimeError("Default registration role has not been bootstrapped")
        user = User(
            email=email,
            password_hash=hash_password(data.password),
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            roles=[default_role],
        )
        self.users.add(user)
        try:
            self.session.flush()
            self.audit.record(
                action="identity.registration",
                resource_type="user",
                resource_id=str(user.id),
                actor_id=user.id,
                success=True,
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateEmailError("An account with this email already exists") from exc
        return user

    def login(self, data: LoginRequest) -> tuple[User, str]:
        email = normalize_email(str(data.email))
        user = self.users.get_by_email(email)
        if user is None:
            hash_password(data.password)
            self._record_failed_login(email=email)
            raise AuthenticationError("Invalid email or password")
        if not user.is_active or not verify_password(data.password, user.password_hash):
            self._record_failed_login(email=email, actor=user)
            raise AuthenticationError("Invalid email or password")

        user.last_login_at = datetime.now(UTC)
        self.audit.record(
            action="identity.login",
            resource_type="user",
            resource_id=str(user.id),
            actor_id=user.id,
            success=True,
        )
        self.session.commit()
        return user, create_access_token(user.id)

    def _record_failed_login(self, *, email: str, actor: User | None = None) -> None:
        self.audit.record(
            action="identity.login",
            resource_type="user",
            resource_id=str(actor.id) if actor else None,
            actor_id=actor.id if actor else None,
            success=False,
            details={"email": email, "reason": "credentials_rejected"},
        )
        self.session.commit()
