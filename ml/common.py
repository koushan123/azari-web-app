"""Versioned artifact persistence shared by the standalone pipelines."""

from __future__ import annotations

import importlib.metadata
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

ARTIFACT_SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class ArtifactMetadata:
    schema_version: str
    pipeline: str
    model_version: str
    trained_at: str
    dataset_fingerprint: str
    feature_schema: list[str]
    random_seed: int
    config: dict[str, Any]
    metrics: dict[str, float]
    dependencies: dict[str, str]
    synthetic_data: bool = True


def dataframe_fingerprint(frame: pd.DataFrame) -> str:
    canonical = frame.sort_index(axis=1).to_csv(index=False, lineterminator="\n")
    return sha256(canonical.encode()).hexdigest()


def dependency_versions() -> dict[str, str]:
    names = ("joblib", "numpy", "pandas", "scikit-learn")
    return {name: importlib.metadata.version(name) for name in names}


def make_metadata(
    *, pipeline: str, model_version: str, data: pd.DataFrame,
    features: list[str], seed: int, config: dict[str, Any], metrics: dict[str, float]
) -> ArtifactMetadata:
    return ArtifactMetadata(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        pipeline=pipeline,
        model_version=model_version,
        trained_at=datetime.now(UTC).isoformat(),
        dataset_fingerprint=dataframe_fingerprint(data),
        feature_schema=features,
        random_seed=seed,
        config=config,
        metrics=metrics,
        dependencies=dependency_versions(),
    )


def save_artifact(path: Path, model: Any, metadata: ArtifactMetadata) -> None:
    path.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path / "model.joblib")
    (path / "metadata.json").write_text(
        json.dumps(asdict(metadata), indent=2, sort_keys=True), encoding="utf-8"
    )


def load_artifact(
    path: Path, *, pipeline: str, expected_features: list[str] | None = None
) -> tuple[Any, ArtifactMetadata]:
    raw = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
    metadata = ArtifactMetadata(**raw)
    if metadata.schema_version != ARTIFACT_SCHEMA_VERSION:
        raise ValueError(f"Unsupported artifact schema: {metadata.schema_version}")
    if metadata.pipeline != pipeline:
        raise ValueError(f"Expected {pipeline!r} artifact, found {metadata.pipeline!r}")
    if expected_features is not None and metadata.feature_schema != expected_features:
        raise ValueError(
            f"Incompatible feature schema: expected {expected_features}, "
            f"found {metadata.feature_schema}"
        )
    return joblib.load(path / "model.joblib"), metadata
