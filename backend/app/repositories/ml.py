"""Persistence queries for Stage 6 ML integration."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models import (
    Invoice,
    MLModelVersion,
    MLPrediction,
    MLPredictionFeedback,
    Party,
    Payment,
    PaymentAllocation,
)


class MLRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_model(self, model: MLModelVersion) -> MLModelVersion:
        self.session.add(model)
        return model

    def model_by_id(self, model_id: UUID) -> MLModelVersion | None:
        return self.session.get(MLModelVersion, model_id)

    def model_by_version(self, pipeline: str, version: str) -> MLModelVersion | None:
        return self.session.scalar(
            select(MLModelVersion).where(
                MLModelVersion.pipeline == pipeline, MLModelVersion.model_version == version
            )
        )

    def models(self, pipeline: str | None = None) -> list[MLModelVersion]:
        statement = select(MLModelVersion)
        if pipeline is not None:
            statement = statement.where(MLModelVersion.pipeline == pipeline)
        return list(self.session.scalars(statement.order_by(MLModelVersion.created_at.desc())))

    def active_model(self, pipeline: str) -> MLModelVersion | None:
        return self.session.scalar(
            select(MLModelVersion).where(
                MLModelVersion.pipeline == pipeline, MLModelVersion.is_active.is_(True)
            )
        )

    def add_prediction(self, prediction: MLPrediction) -> MLPrediction:
        self.session.add(prediction)
        return prediction

    def prediction(self, prediction_id: UUID) -> MLPrediction | None:
        return self.session.scalar(
            select(MLPrediction)
            .options(selectinload(MLPrediction.feedback))
            .where(MLPrediction.id == prediction_id)
        )

    def predictions(self, pipeline: str | None = None) -> list[MLPrediction]:
        statement = select(MLPrediction).options(selectinload(MLPrediction.feedback))
        if pipeline is not None:
            statement = statement.where(MLPrediction.pipeline == pipeline)
        return list(self.session.scalars(statement.order_by(MLPrediction.predicted_at.desc())))

    def add_feedback(self, feedback: MLPredictionFeedback) -> MLPredictionFeedback:
        self.session.add(feedback)
        return feedback

    def invoice(self, invoice_id: UUID) -> Invoice | None:
        return self.session.scalar(
            select(Invoice).options(selectinload(Invoice.customer)).where(Invoice.id == invoice_id)
        )

    def customer_invoices(self, customer_id: UUID, as_of: date) -> list[Invoice]:
        return list(
            self.session.scalars(
                select(Invoice)
                .where(
                    Invoice.customer_id == customer_id,
                    Invoice.issue_date <= as_of,
                    Invoice.status.in_(("ISSUED", "PARTIALLY_PAID", "PAID")),
                )
                .order_by(Invoice.issue_date, Invoice.id)
            )
        )

    def posted_allocations(self, as_of: date) -> list[tuple[PaymentAllocation, Payment]]:
        return list(
            self.session.execute(
                select(PaymentAllocation, Payment)
                .join(Payment)
                .where(Payment.status == "POSTED", Payment.payment_date <= as_of)
            ).tuples()
        )

    def posted_payments(self, as_of: date) -> list[Payment]:
        return list(
            self.session.scalars(
                select(Payment)
                .where(Payment.status == "POSTED", Payment.payment_date <= as_of)
                .order_by(Payment.payment_date)
            )
        )

    def customer(self, customer_id: UUID) -> Party | None:
        return self.session.scalar(
            select(Party).where(Party.id == customer_id, Party.is_customer.is_(True))
        )
