"""Temporal payment-delay risk modelling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

from ml.common import ArtifactMetadata, load_artifact, make_metadata, save_artifact
from ml.preprocessing.payment_features import PAYMENT_FEATURES, build_payment_features


@dataclass(frozen=True)
class RiskPrediction:
    risk_classification: str
    probability: float
    model_version: str
    feature_contributions: dict[str, float]
    explanation_scope: str = "model-level heuristic"


@dataclass
class PaymentRiskModel:
    estimator: RandomForestClassifier
    metadata: ArtifactMetadata
    baseline: dict[str, float]
    risk_threshold: float

    def predict(self, features: dict[str, float]) -> RiskPrediction:
        frame = pd.DataFrame([{name: features[name] for name in PAYMENT_FEATURES}])
        probability = float(self.estimator.predict_proba(frame)[0, 1])
        contributions = {
            name: float((features[name] - self.baseline[name]) * importance)
            for name, importance in zip(
                PAYMENT_FEATURES, self.estimator.feature_importances_, strict=True
            )
        }
        ordered = dict(
            sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True)
        )
        classification = "high" if probability >= self.risk_threshold else "low"
        return RiskPrediction(
            classification, probability, self.metadata.model_version, ordered
        )


def temporal_split(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ordered = frame.sort_values("prediction_time").reset_index(drop=True)
    train_end = int(len(ordered) * 0.70)
    validation_end = int(len(ordered) * 0.85)
    return (
        ordered.iloc[:train_end],
        ordered.iloc[train_end:validation_end],
        ordered.iloc[validation_end:],
    )


def train_payment_risk_model(
    events: pd.DataFrame,
    *,
    seed: int,
    delay_days: int = 7,
    risk_threshold: float = 0.5,
    model_version: str = "payment-risk-v1",
) -> tuple[
    PaymentRiskModel, dict[str, float], tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
]:
    features = build_payment_features(events, delay_days)
    train, validation, test = temporal_split(features)
    estimator = RandomForestClassifier(
        n_estimators=180,
        max_depth=8,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=seed,
        n_jobs=1,
    )
    estimator.fit(train[PAYMENT_FEATURES], train["delayed"])
    probabilities = estimator.predict_proba(test[PAYMENT_FEATURES])[:, 1]
    predictions = (probabilities >= risk_threshold).astype(int)
    metrics = {
        "accuracy": float(accuracy_score(test["delayed"], predictions)),
        "f1": float(f1_score(test["delayed"], predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(test["delayed"], probabilities)),
        "validation_roc_auc": float(
            roc_auc_score(
                validation["delayed"],
                estimator.predict_proba(validation[PAYMENT_FEATURES])[:, 1],
            )
        ),
    }
    metadata = make_metadata(
        pipeline="payment_delay_risk",
        model_version=model_version,
        data=events,
        features=PAYMENT_FEATURES,
        seed=seed,
        config={"delay_days": delay_days, "risk_threshold": risk_threshold},
        metrics=metrics,
    )
    baseline = {name: float(train[name].mean()) for name in PAYMENT_FEATURES}
    return (
        PaymentRiskModel(estimator, metadata, baseline, risk_threshold),
        metrics,
        (train, validation, test),
    )


def save_payment_risk_model(model: PaymentRiskModel, path: Path) -> None:
    save_artifact(
        path, {"estimator": model.estimator, "baseline": model.baseline}, model.metadata
    )


def load_payment_risk_model(path: Path) -> PaymentRiskModel:
    state, metadata = load_artifact(
        path, pipeline="payment_delay_risk", expected_features=PAYMENT_FEATURES
    )
    return PaymentRiskModel(
        state["estimator"],
        metadata,
        state["baseline"],
        float(metadata.config["risk_threshold"]),
    )
