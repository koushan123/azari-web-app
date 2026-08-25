from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest
from sklearn.model_selection import train_test_split

from ml.common import dataframe_fingerprint
from ml.config import MLConfig
from ml.inference.cash_flow import CashFlowModel
from ml.inference.payment_risk import PaymentRiskModel
from ml.inference.segmentation import SegmentationModel
from ml.inference.transaction import TransactionModel
from ml.preprocessing.payment_features import PAYMENT_FEATURES, build_payment_features
from ml.synthetic import cash_flow_data, customer_data, payment_data, transaction_data
from ml.training.cash_flow import (
    chronological_backtest_split,
    load_cash_flow_model,
    save_cash_flow_model,
    train_cash_flow_model,
)
from ml.training.payment_risk import (
    load_payment_risk_model,
    save_payment_risk_model,
    train_payment_risk_model,
)
from ml.training.segmentation import (
    SEGMENT_FEATURES,
    load_segmentation_model,
    save_segmentation_model,
    train_segmentation_model,
)
from ml.training.transaction import (
    load_transaction_model,
    save_transaction_model,
    train_transaction_model,
)


def test_synthetic_generators_are_reproducible_and_labeled() -> None:
    generators = (transaction_data, payment_data, cash_flow_data, customer_data)
    for generator in generators:
        first = generator(19)
        second = generator(19)
        pd.testing.assert_frame_equal(first, second)
        assert first["is_synthetic"].all()
        assert dataframe_fingerprint(first) == dataframe_fingerprint(second)


def test_environment_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ML_RANDOM_SEED", "8")
    monkeypatch.setenv("ML_CONFIDENCE_THRESHOLD", "0.72")
    monkeypatch.setenv("ML_RISK_DELAY_DAYS", "10")
    monkeypatch.setenv("ML_FORECAST_HORIZON", "14")
    assert MLConfig.from_env() == MLConfig(8, 0.72, 10, 14)
    assert all((TransactionModel, PaymentRiskModel, CashFlowModel, SegmentationModel))


def test_transaction_comparison_threshold_and_round_trip(tmp_path: Path) -> None:
    data = transaction_data(7, 400)
    model, scores = train_transaction_model(data, seed=7, confidence_threshold=0.999)
    assert set(scores) == {"multinomial_nb", "calibrated_linear_svm"}
    prediction = model.predict("unknown miscellaneous transfer")
    assert 0 <= prediction.confidence <= 1
    assert prediction.manual_review
    save_transaction_model(model, tmp_path)
    assert load_transaction_model(tmp_path).predict(
        "hotel booking metro"
    ) == model.predict("hotel booking metro")


def test_transaction_vectorizer_is_fitted_only_on_training_rows() -> None:
    data = transaction_data(31, 300)
    _, test = train_test_split(
        data, test_size=0.25, random_state=31, stratify=data["category"]
    )
    data.loc[test.index[:2], "description"] += " testonlysentinel"
    model, _ = train_transaction_model(data, seed=31, confidence_threshold=0.7)
    assert "testonlysentinel" not in model.estimator.named_steps["tfidf"].vocabulary_


def test_payment_features_do_not_leak_future_outcomes() -> None:
    events = payment_data(11, customers=5, invoices=7)
    before = build_payment_features(events)
    last_index = events.groupby("customer_id")["invoice_date"].idxmax().iloc[0]
    changed = events.copy()
    changed.loc[last_index, "payment_date"] = pd.Timestamp("2035-01-01")
    after = build_payment_features(changed)
    invoice_id = changed.loc[last_index, "invoice_id"]
    columns = ["invoice_id", *PAYMENT_FEATURES]
    pd.testing.assert_frame_equal(
        before.loc[before["invoice_id"] == invoice_id, columns].reset_index(drop=True),
        after.loc[after["invoice_id"] == invoice_id, columns].reset_index(drop=True),
    )
    with pytest.raises(ValueError, match="Missing payment columns"):
        build_payment_features(events.drop(columns="due_date"))


def test_payment_temporal_split_prediction_and_round_trip(tmp_path: Path) -> None:
    model, metrics, splits = train_payment_risk_model(payment_data(4), seed=4)
    train, validation, test = splits
    assert train["prediction_time"].max() <= validation["prediction_time"].min()
    assert validation["prediction_time"].max() <= test["prediction_time"].min()
    assert 0 <= metrics["roc_auc"] <= 1
    sample = {name: float(test.iloc[0][name]) for name in PAYMENT_FEATURES}
    prediction = model.predict(sample)
    assert 0 <= prediction.probability <= 1
    assert prediction.risk_classification in {"high", "low"}
    assert prediction.explanation_scope == "model-level heuristic"
    save_payment_risk_model(model, tmp_path)
    assert load_payment_risk_model(tmp_path).predict(sample) == prediction


def test_forecast_backtest_intervals_and_round_trip(tmp_path: Path) -> None:
    data = cash_flow_data(5, 260)
    train, test = chronological_backtest_split(data.sample(frac=1, random_state=5), 21)
    assert pd.Timestamp(train["date"].max()) < pd.Timestamp(test["date"].min())
    model, metrics = train_cash_flow_model(data, seed=5, horizon=21)
    assert metrics["mae"] > 0
    assert metrics["rmse"] >= metrics["mae"]
    forecast = model.forecast(12)
    assert len(forecast) == 12
    assert all(point.lower < point.predicted < point.upper for point in forecast)
    save_cash_flow_model(model, tmp_path)
    assert load_cash_flow_model(tmp_path).forecast(12) == forecast
    with pytest.raises(ValueError, match="longer"):
        train_cash_flow_model(cash_flow_data(5, 10), seed=5, horizon=10)


def test_segmentation_selection_descriptions_and_round_trip(tmp_path: Path) -> None:
    data = customer_data(9, 180)
    model, evaluations = train_segmentation_model(data, seed=9, candidate_k=(2, 3, 4))
    assert set(evaluations) == {2, 3, 4}
    assert all(
        {"inertia", "silhouette"} == set(metrics) for metrics in evaluations.values()
    )
    sample = {name: float(data.iloc[0][name]) for name in SEGMENT_FEATURES}
    prediction = model.predict(sample)
    assert "customers" in prediction.description
    train, _ = train_test_split(data, test_size=0.2, random_state=9)
    assert model.scaler.mean_[0] == pytest.approx(train["invoice_count"].mean())
    save_segmentation_model(model, tmp_path)
    assert load_segmentation_model(tmp_path).predict(sample) == prediction


def test_artifact_schema_validation(tmp_path: Path) -> None:
    model, _ = train_cash_flow_model(cash_flow_data(3, 100), seed=3, horizon=10)
    save_cash_flow_model(model, tmp_path)
    metadata_path = tmp_path / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["schema_version"] = "999"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported artifact schema"):
        load_cash_flow_model(tmp_path)


def test_artifact_pipeline_validation(tmp_path: Path) -> None:
    model, _ = train_cash_flow_model(cash_flow_data(3, 100), seed=3, horizon=10)
    save_cash_flow_model(model, tmp_path)
    from ml.common import load_artifact

    with pytest.raises(ValueError, match="Expected"):
        load_artifact(tmp_path, pipeline="another_pipeline")
    with pytest.raises(ValueError, match="Incompatible feature schema"):
        load_artifact(
            tmp_path, pipeline="cash_flow_forecast", expected_features=["wrong_feature"]
        )


def test_training_is_reproducible_except_timestamp() -> None:
    data = transaction_data(23, 300)
    first, first_scores = train_transaction_model(
        data, seed=23, confidence_threshold=0.7
    )
    second, second_scores = train_transaction_model(
        data, seed=23, confidence_threshold=0.7
    )
    assert first_scores == second_scores
    assert replace(first.metadata, trained_at="") == replace(
        second.metadata, trained_at=""
    )
    assert first.predict("cloud subscription monthly") == second.predict(
        "cloud subscription monthly"
    )
