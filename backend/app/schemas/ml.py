"""Validated Stage 6 ML API contracts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

PipelineName = Literal[
    "transaction_classification",
    "payment_delay_risk",
    "cash_flow_forecast",
    "customer_segmentation",
]


class ModelRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pipeline: PipelineName
    artifact_identifier: str = Field(pattern=r"^[a-z0-9-]+/[A-Za-z0-9._-]+$", max_length=255)


class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    pipeline: str
    model_version: str
    artifact_schema_version: str
    dataset_fingerprint: str
    feature_schema: list[str]
    training_configuration: dict[str, Any]
    metrics: dict[str, float]
    dependencies: dict[str, str]
    synthetic_data: bool
    is_active: bool
    activated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TransactionClassifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=3, max_length=500)
    source_reference: str | None = Field(default=None, max_length=100)


class TransactionPredictionResponse(BaseModel):
    prediction_id: UUID
    category: str
    confidence: float
    manual_review: bool
    model_version: str
    prediction_timestamp: datetime


class PaymentRiskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_id: UUID
    as_of: date | None = None


class PaymentRiskResponse(BaseModel):
    prediction_id: UUID
    invoice_id: UUID
    risk_category: str
    probability: float
    model_version: str
    explanation: dict[str, float]
    explanation_scope: str
    prediction_timestamp: datetime
    as_of: date


class CashFlowForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    horizon: int = Field(default=30, ge=1, le=365)
    as_of: date | None = None


class ForecastPointResponse(BaseModel):
    date: date
    predicted: float
    lower: float
    upper: float


class CashFlowForecastResponse(BaseModel):
    prediction_id: UUID
    model_version: str
    forecast_timestamp: datetime
    as_of: date
    horizon: int
    points: list[ForecastPointResponse]


class SegmentationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    party_id: UUID
    as_of: date | None = None


class SegmentationResponse(BaseModel):
    prediction_id: UUID
    party_id: UUID
    segment: int
    behavioral_description: str
    model_version: str
    prediction_timestamp: datetime
    as_of: date


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feedback_type: Literal["VERIFIED", "CORRECTION", "COMMENT"]
    actual_value: str | None = Field(default=None, min_length=1, max_length=500)
    comment: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_content(self) -> FeedbackRequest:
        if self.feedback_type in {"VERIFIED", "CORRECTION"} and self.actual_value is None:
            raise ValueError("actual_value is required for verified or corrected feedback")
        if self.feedback_type == "COMMENT" and self.comment is None:
            raise ValueError("comment is required for comment feedback")
        return self


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    prediction_id: UUID
    feedback_type: str
    actual_value: str | None
    comment: str | None
    submitted_by_id: UUID | None
    submitted_at: datetime


class PredictionHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    model_version_id: UUID
    pipeline: str
    source_type: str | None
    source_id: str | None
    predicted_value: dict[str, Any]
    confidence: float | None
    review_required: bool | None
    explanation: dict[str, Any] | None
    requested_by_id: UUID | None
    predicted_at: datetime
    feedback: list[FeedbackResponse]
