"""Versioned artifact persistence shared by the standalone pipelines."""

from __future__ import annotations

import hmac
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
    *,
    pipeline: str,
    model_version: str,
    data: pd.DataFrame,
    features: list[str],
    seed: int,
    config: dict[str, Any],
    metrics: dict[str, float],
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


def _metadata(
    raw: bytes, *, pipeline: str, expected_features: list[str] | None
) -> ArtifactMetadata:
    metadata = ArtifactMetadata(**json.loads(raw.decode("utf-8")))
    if metadata.schema_version != ARTIFACT_SCHEMA_VERSION:
        raise ValueError(f"Unsupported artifact schema: {metadata.schema_version}")
    if metadata.pipeline != pipeline:
        raise ValueError(f"Expected {pipeline!r} artifact, found {metadata.pipeline!r}")
    if expected_features is not None and metadata.feature_schema != expected_features:
        raise ValueError(
            f"Incompatible feature schema: expected {expected_features}, "
            f"found {metadata.feature_schema}"
        )
    return metadata


def inspect_artifact(
    path: Path, *, pipeline: str, expected_features: list[str] | None = None
) -> tuple[ArtifactMetadata, str]:
    """Validate inert metadata and hash the artifact without deserializing it."""
    metadata_raw = (path / "metadata.json").read_bytes()
    metadata = _metadata(metadata_raw, pipeline=pipeline, expected_features=expected_features)
    digest = sha256()
    digest.update(b"metadata.json\0")
    digest.update(metadata_raw)
    digest.update(b"model.joblib\0")
    with (path / "model.joblib").open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return metadata, digest.hexdigest()


def load_artifact(
    path: Path,
    *,
    pipeline: str,
    expected_features: list[str] | None = None,
    expected_digest: str | None = None,
) -> tuple[Any, ArtifactMetadata]:
    metadata_raw = (path / "metadata.json").read_bytes()
    metadata = _metadata(metadata_raw, pipeline=pipeline, expected_features=expected_features)
    with (path / "model.joblib").open("rb") as model_file:
        digest = sha256()
        digest.update(b"metadata.json\0")
        digest.update(metadata_raw)
        digest.update(b"model.joblib\0")
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
        actual_digest = digest.hexdigest()
        if expected_digest is not None and not hmac.compare_digest(
            actual_digest, expected_digest
        ):
            raise ValueError("Artifact integrity is not trusted")
        model_file.seek(0)
        return joblib.load(model_file), metadata
