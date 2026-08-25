"""Transaction-description classification training and inference."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from ml.common import ArtifactMetadata, load_artifact, make_metadata, save_artifact
from ml.evaluation.metrics import classification_metrics


@dataclass(frozen=True)
class TransactionPrediction:
    category: str
    confidence: float
    manual_review: bool
    model_version: str


@dataclass
class TransactionModel:
    estimator: Any
    metadata: ArtifactMetadata
    confidence_threshold: float

    def predict(self, description: str) -> TransactionPrediction:
        probabilities = np.asarray(self.estimator.predict_proba([description]))[0]
        position = int(np.argmax(probabilities))
        confidence = float(probabilities[position])
        category = str(self.estimator.classes_[position])
        return TransactionPrediction(
            category,
            confidence,
            confidence < self.confidence_threshold,
            self.metadata.model_version,
        )


def train_transaction_model(
    data: pd.DataFrame,
    *,
    seed: int,
    confidence_threshold: float,
    model_version: str = "transaction-v1",
) -> tuple[TransactionModel, dict[str, dict[str, float]]]:
    train, test = train_test_split(
        data, test_size=0.25, random_state=seed, stratify=data["category"]
    )
    candidates: dict[str, Pipeline] = {
        "multinomial_nb": Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2)),
                ("classifier", MultinomialNB()),
            ]
        ),
        "calibrated_linear_svm": Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2)),
                (
                    "classifier",
                    CalibratedClassifierCV(LinearSVC(random_state=seed), cv=3),
                ),
            ]
        ),
    }
    scores: dict[str, dict[str, float]] = {}
    for name, estimator in candidates.items():
        estimator.fit(train["description"], train["category"])
        prediction = estimator.predict(test["description"])
        scores[name] = classification_metrics(test["category"], prediction)
    selected_name = max(
        scores, key=lambda name: (scores[name]["macro_f1"], scores[name]["accuracy"])
    )
    estimator = candidates[selected_name]
    metadata = make_metadata(
        pipeline="transaction_classification",
        model_version=model_version,
        data=data,
        features=["description"],
        seed=seed,
        config={
            "confidence_threshold": confidence_threshold,
            "selected_model": selected_name,
        },
        metrics=scores[selected_name],
    )
    return TransactionModel(estimator, metadata, confidence_threshold), scores


def save_transaction_model(model: TransactionModel, path: Path) -> None:
    save_artifact(path, model.estimator, model.metadata)


def load_transaction_model(path: Path) -> TransactionModel:
    estimator, metadata = load_artifact(
        path, pipeline="transaction_classification", expected_features=["description"]
    )
    threshold = float(metadata.config["confidence_threshold"])
    return TransactionModel(estimator, metadata, threshold)
