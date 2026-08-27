"""Controlled artifact resolution, validation, and thread-safe model caching."""

from __future__ import annotations

import importlib.metadata
import os
import re
from collections.abc import Callable
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import UUID

from ml.common import ARTIFACT_SCHEMA_VERSION, ArtifactMetadata, inspect_artifact
from ml.preprocessing.payment_features import PAYMENT_FEATURES
from ml.training.cash_flow import load_cash_flow_model
from ml.training.payment_risk import load_payment_risk_model
from ml.training.segmentation import SEGMENT_FEATURES, load_segmentation_model
from ml.training.transaction import load_transaction_model

from backend.app.db.models import MLModelVersion

PIPELINES = {
    "transaction_classification",
    "payment_delay_risk",
    "cash_flow_forecast",
    "customer_segmentation",
}
LOADERS: dict[str, Callable[[Path, str | None], Any]] = {
    "transaction_classification": load_transaction_model,
    "payment_delay_risk": load_payment_risk_model,
    "cash_flow_forecast": load_cash_flow_model,
    "customer_segmentation": load_segmentation_model,
}
EXPECTED_FEATURES = {
    "transaction_classification": ["description"],
    "payment_delay_risk": PAYMENT_FEATURES,
    "cash_flow_forecast": ["date", "net_cash_flow"],
    "customer_segmentation": SEGMENT_FEATURES,
}
ARTIFACT_IDENTIFIER = re.compile(r"^[a-z0-9-]+/[A-Za-z0-9._-]+$")


class MLIntegrationError(ValueError):
    """Safe base error for ML application failures."""


class ModelNotFoundError(MLIntegrationError):
    pass


class NoActiveModelError(MLIntegrationError):
    pass


class ArtifactValidationError(MLIntegrationError):
    pass


class PredictionInputError(MLIntegrationError):
    pass


class PredictionExecutionError(MLIntegrationError):
    pass


class FeedbackConflictError(MLIntegrationError):
    pass


class ArtifactRegistry:
    def __init__(self, model_dir: Path, *, require_read_only: bool = False) -> None:
        self.model_dir = model_dir.resolve()
        self.require_read_only = require_read_only

    def resolve(self, identifier: str) -> Path:
        if not ARTIFACT_IDENTIFIER.fullmatch(identifier):
            raise ArtifactValidationError("Invalid artifact identifier")
        candidate = (self.model_dir / identifier).resolve()
        if self.model_dir not in candidate.parents:
            raise ArtifactValidationError("Invalid artifact identifier")
        return candidate

    def validate(self, pipeline: str, identifier: str) -> tuple[ArtifactMetadata, str]:
        """Inspect metadata and compute integrity without deserializing joblib."""
        if pipeline not in PIPELINES:
            raise ArtifactValidationError("Unsupported ML pipeline")
        path = self.resolve(identifier)
        if not path.is_dir():
            raise ArtifactValidationError("Registered artifact is unavailable")
        try:
            metadata, digest = inspect_artifact(
                path,
                pipeline=pipeline,
                expected_features=EXPECTED_FEATURES[pipeline],
            )
        except Exception as exc:
            raise ArtifactValidationError("Artifact validation failed") from exc
        if metadata.schema_version != ARTIFACT_SCHEMA_VERSION:
            raise ArtifactValidationError("Unsupported artifact schema version")
        if metadata.model_version != path.name:
            raise ArtifactValidationError("Artifact version does not match its identifier")
        for dependency, trained_version in metadata.dependencies.items():
            try:
                runtime_version = importlib.metadata.version(dependency)
            except importlib.metadata.PackageNotFoundError as exc:
                raise ArtifactValidationError("Artifact runtime dependency is unavailable") from exc
            if runtime_version.split(".", 1)[0] != trained_version.split(".", 1)[0]:
                raise ArtifactValidationError("Artifact runtime dependency is incompatible")
        return metadata, digest

    def load(self, pipeline: str, identifier: str, expected_digest: str | None) -> Any:
        if expected_digest is None:
            raise ArtifactValidationError("Artifact integrity has not been approved")
        metadata, digest = self.validate(pipeline, identifier)
        if digest != expected_digest:
            raise ArtifactValidationError("Artifact integrity validation failed")
        path = self.resolve(identifier)
        if self.require_read_only and any(
            os.access(candidate, os.W_OK)
            for candidate in (path, path / "metadata.json", path / "model.joblib")
        ):
            raise ArtifactValidationError("Production artifacts must be read-only")
        try:
            model = LOADERS[pipeline](path, expected_digest)
        except Exception as exc:
            raise ArtifactValidationError("Artifact validation failed") from exc
        if model.metadata != metadata:
            raise ArtifactValidationError("Artifact metadata changed during loading")
        return model


class ModelCache:
    def __init__(self) -> None:
        self._models: dict[UUID, Any] = {}
        self._lock = RLock()

    def get_or_load(self, record: MLModelVersion, registry: ArtifactRegistry) -> Any:
        with self._lock:
            if record.id in self._models:
                return self._models[record.id]
            model = registry.load(
                record.pipeline, record.artifact_identifier, record.artifact_digest
            )
            metadata: ArtifactMetadata = model.metadata
            if metadata.model_version != record.model_version:
                raise ArtifactValidationError("Registered model metadata is incompatible")
            if metadata.dataset_fingerprint != record.dataset_fingerprint:
                raise ArtifactValidationError("Registered artifact fingerprint is incompatible")
            self._models[record.id] = model
            return model

    def invalidate(self, pipeline: str, records: list[MLModelVersion]) -> None:
        with self._lock:
            for record in records:
                if record.pipeline == pipeline:
                    self._models.pop(record.id, None)

    def clear(self) -> None:
        with self._lock:
            self._models.clear()


model_cache = ModelCache()
