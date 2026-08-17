from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, UUIDPrimaryKeyMixin


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    """Append-oriented security and identity event."""

    __tablename__ = "audit_events"

    actor_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)

    actor: Mapped["User | None"] = relationship(back_populates="audit_events")


from backend.app.db.models.identity import User  # noqa: E402
