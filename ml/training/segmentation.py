"""Customer segmentation with scaled K-means model selection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from ml.common import ArtifactMetadata, load_artifact, make_metadata, save_artifact

SEGMENT_FEATURES = [
    "invoice_count",
    "total_invoice_amount",
    "avg_invoice_amount",
    "total_payment_amount",
    "avg_delay_days",
    "outstanding_balance",
    "payment_frequency",
]


@dataclass(frozen=True)
class SegmentPrediction:
    segment: int
    description: str
    model_version: str


@dataclass
class SegmentationModel:
    scaler: StandardScaler
    estimator: KMeans
    descriptions: dict[int, str]
    metadata: ArtifactMetadata

    def predict(self, customer: dict[str, float]) -> SegmentPrediction:
        frame = pd.DataFrame([{name: customer[name] for name in SEGMENT_FEATURES}])
        segment = int(self.estimator.predict(self.scaler.transform(frame))[0])
        return SegmentPrediction(
            segment, self.descriptions[segment], self.metadata.model_version
        )


def _describe_centroids(scaler: StandardScaler, estimator: KMeans) -> dict[int, str]:
    centroids = pd.DataFrame(
        scaler.inverse_transform(estimator.cluster_centers_), columns=SEGMENT_FEATURES
    )
    medians = centroids.median()
    descriptions: dict[int, str] = {}
    for segment, row in centroids.iterrows():
        value = (
            "high-value"
            if row["total_invoice_amount"] >= medians["total_invoice_amount"]
            else "lower-value"
        )
        timing = (
            "slow-paying"
            if row["avg_delay_days"] >= medians["avg_delay_days"]
            else "reliable-paying"
        )
        balance = (
            "high-outstanding"
            if row["outstanding_balance"] >= medians["outstanding_balance"]
            else "low-outstanding"
        )
        descriptions[int(segment)] = f"{value}, {timing}, {balance} customers"
    return descriptions


def train_segmentation_model(
    data: pd.DataFrame,
    *,
    seed: int,
    candidate_k: tuple[int, ...] = (2, 3, 4, 5, 6),
    model_version: str = "customer-segments-v1",
) -> tuple[SegmentationModel, dict[int, dict[str, float]]]:
    train, _ = train_test_split(data, test_size=0.2, random_state=seed)
    scaler = StandardScaler().fit(train[SEGMENT_FEATURES])
    scaled = scaler.transform(train[SEGMENT_FEATURES])
    evaluations: dict[int, dict[str, float]] = {}
    candidates: dict[int, KMeans] = {}
    for k in candidate_k:
        estimator = KMeans(n_clusters=k, n_init=20, random_state=seed).fit(scaled)
        candidates[k] = estimator
        evaluations[k] = {
            "inertia": float(estimator.inertia_),
            "silhouette": float(silhouette_score(scaled, estimator.labels_)),
        }
    selected_k = max(evaluations, key=lambda k: (evaluations[k]["silhouette"], -k))
    estimator = candidates[selected_k]
    metrics = {
        "selected_k": float(selected_k),
        "silhouette": evaluations[selected_k]["silhouette"],
        "inertia": evaluations[selected_k]["inertia"],
    }
    metadata = make_metadata(
        pipeline="customer_segmentation",
        model_version=model_version,
        data=data,
        features=SEGMENT_FEATURES,
        seed=seed,
        config={"candidate_k": list(candidate_k)},
        metrics=metrics,
    )
    model = SegmentationModel(
        scaler, estimator, _describe_centroids(scaler, estimator), metadata
    )
    return model, evaluations


def save_segmentation_model(model: SegmentationModel, path: Path) -> None:
    state: dict[str, Any] = {
        "scaler": model.scaler,
        "estimator": model.estimator,
        "descriptions": model.descriptions,
    }
    save_artifact(path, state, model.metadata)


def load_segmentation_model(path: Path, expected_digest: str | None = None) -> SegmentationModel:
    state, metadata = load_artifact(
        path,
        pipeline="customer_segmentation",
        expected_features=SEGMENT_FEATURES,
        expected_digest=expected_digest,
    )
    return SegmentationModel(
        state["scaler"], state["estimator"], state["descriptions"], metadata
    )
