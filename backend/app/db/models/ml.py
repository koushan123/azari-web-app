"""Persistent model registry, predictions, and append-only feedback."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.db.models.identity import User

JSON_VALUE = JSON().with_variant(JSONB, "postgresql")
PIPELINE_CHECK = (
    "pipeline IN ('transaction_classification','payment_delay_risk',"
    "'cash_flow_forecast','customer_segmentation')"
)


class MLModelVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ml_model_versions"
    __table_args__ = (
        UniqueConstraint("pipeline", "model_version", name="uq_ml_model_versions_pipeline_version"),
        CheckConstraint(PIPELINE_CHECK, name="valid_pipeline"),
        Index("ix_ml_model_versions_pipeline_active", "pipeline", "is_active"),
        Index(
            "uq_ml_model_versions_one_active_pipeline",
            "pipeline",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active = 1"),
        ),
    )

    pipeline: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    artifact_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_schema_version: Mapped[str] = mapped_column(String(30), nullable=False)
    dataset_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_schema: Mapped[list[str]] = mapped_column(JSON_VALUE, nullable=False)
    training_configuration: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, nullable=False)
    metrics: Mapped[dict[str, float]] = mapped_column(JSON_VALUE, nullable=False)
    dependencies: Mapped[dict[str, str]] = mapped_column(JSON_VALUE, nullable=False)
    synthetic_data: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[User | None] = relationship()
    predictions: Mapped[list[MLPrediction]] = relationship(back_populates="model_version")


class MLPrediction(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ml_predictions"
    __table_args__ = (
        CheckConstraint(PIPELINE_CHECK, name="valid_pipeline"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="valid_confidence"
        ),
        Index("ix_ml_predictions_pipeline_predicted_at", "pipeline", "predicted_at"),
        Index("ix_ml_predictions_model_version_id", "model_version_id"),
        Index("ix_ml_predictions_source", "source_type", "source_id"),
    )

    model_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ml_model_versions.id", ondelete="RESTRICT"), nullable=False
    )
    pipeline: Mapped[str] = mapped_column(String(50), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(50))
    source_id: Mapped[str | None] = mapped_column(String(100))
    predicted_value: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    review_required: Mapped[bool | None] = mapped_column(Boolean)
    explanation: Mapped[dict[str, Any] | None] = mapped_column(JSON_VALUE)
    requested_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    model_version: Mapped[MLModelVersion] = relationship(back_populates="predictions")
    requested_by: Mapped[User | None] = relationship()
    feedback: Mapped[list[MLPredictionFeedback]] = relationship(back_populates="prediction")


class MLPredictionFeedback(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ml_prediction_feedback"
    __table_args__ = (
        CheckConstraint(
            "feedback_type IN ('VERIFIED','CORRECTION','COMMENT')", name="valid_feedback_type"
        ),
        Index("ix_ml_prediction_feedback_prediction_id", "prediction_id"),
    )

    prediction_id: Mapped[UUID] = mapped_column(
        ForeignKey("ml_predictions.id", ondelete="RESTRICT"), nullable=False
    )
    actual_value: Mapped[str | None] = mapped_column(String(500))
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    submitted_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    prediction: Mapped[MLPrediction] = relationship(back_populates="feedback")
    submitted_by: Mapped[User | None] = relationship()
