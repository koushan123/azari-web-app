"""Add Stage 6 ML registry, predictions, and feedback.

Revision ID: 20260825_0003
Revises: 20260818_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260825_0003"
down_revision: str | None = "20260818_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PIPELINE = (
    "pipeline IN ('transaction_classification','payment_delay_risk',"
    "'cash_flow_forecast','customer_segmentation')"
)


def upgrade() -> None:
    op.create_table(
        "ml_model_versions",
        sa.Column("pipeline", sa.String(50), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("artifact_identifier", sa.String(255), nullable=False),
        sa.Column("artifact_schema_version", sa.String(30), nullable=False),
        sa.Column("dataset_fingerprint", sa.String(64), nullable=False),
        sa.Column("feature_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "training_configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dependencies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synthetic_data", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_id", sa.Uuid()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(PIPELINE, name="valid_pipeline"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_ml_model_versions"),
        sa.UniqueConstraint(
            "pipeline", "model_version", name="uq_ml_model_versions_pipeline_version"
        ),
    )
    op.create_index(
        "ix_ml_model_versions_pipeline_active", "ml_model_versions", ["pipeline", "is_active"]
    )
    op.create_index(
        "uq_ml_model_versions_one_active_pipeline",
        "ml_model_versions",
        ["pipeline"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.create_table(
        "ml_predictions",
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline", sa.String(50), nullable=False),
        sa.Column("source_type", sa.String(50)),
        sa.Column("source_id", sa.String(100)),
        sa.Column("predicted_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("review_required", sa.Boolean()),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("requested_by_id", sa.Uuid()),
        sa.Column(
            "predicted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(PIPELINE, name="valid_pipeline"),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="valid_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"], ["ml_model_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_ml_predictions"),
    )
    op.create_index(
        "ix_ml_predictions_pipeline_predicted_at", "ml_predictions", ["pipeline", "predicted_at"]
    )
    op.create_index("ix_ml_predictions_model_version_id", "ml_predictions", ["model_version_id"])
    op.create_index("ix_ml_predictions_source", "ml_predictions", ["source_type", "source_id"])
    op.create_table(
        "ml_prediction_feedback",
        sa.Column("prediction_id", sa.Uuid(), nullable=False),
        sa.Column("actual_value", sa.String(500)),
        sa.Column("feedback_type", sa.String(20), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("submitted_by_id", sa.Uuid()),
        sa.Column(
            "submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "feedback_type IN ('VERIFIED','CORRECTION','COMMENT')",
            name="valid_feedback_type",
        ),
        sa.ForeignKeyConstraint(["prediction_id"], ["ml_predictions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_ml_prediction_feedback"),
    )
    op.create_index(
        "ix_ml_prediction_feedback_prediction_id", "ml_prediction_feedback", ["prediction_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_ml_prediction_feedback_prediction_id", table_name="ml_prediction_feedback")
    op.drop_table("ml_prediction_feedback")
    op.drop_index("ix_ml_predictions_source", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_model_version_id", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_pipeline_predicted_at", table_name="ml_predictions")
    op.drop_table("ml_predictions")
    op.drop_index("uq_ml_model_versions_one_active_pipeline", table_name="ml_model_versions")
    op.drop_index("ix_ml_model_versions_pipeline_active", table_name="ml_model_versions")
    op.drop_table("ml_model_versions")
