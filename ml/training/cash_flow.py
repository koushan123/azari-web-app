"""Deterministic cash-flow forecasting with chronological backtesting.

This lightweight harmonic linear model is the documented Prophet fallback. It
keeps Python 3.12 installation and inference deterministic without introducing
Prophet's compiled dependency stack.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from ml.common import ArtifactMetadata, load_artifact, make_metadata, save_artifact
from ml.evaluation.metrics import regression_metrics


def _design_matrix(offsets: np.ndarray) -> np.ndarray:
    return np.column_stack(
        [
            offsets,
            np.sin(2 * np.pi * offsets / 7),
            np.cos(2 * np.pi * offsets / 7),
            np.sin(2 * np.pi * offsets / 30.5),
            np.cos(2 * np.pi * offsets / 30.5),
            np.sin(2 * np.pi * offsets / 365.25),
            np.cos(2 * np.pi * offsets / 365.25),
        ]
    )


@dataclass(frozen=True)
class ForecastPoint:
    date: str
    predicted: float
    lower: float
    upper: float
    model_version: str


@dataclass
class CashFlowModel:
    estimator: LinearRegression
    metadata: ArtifactMetadata
    origin: pd.Timestamp
    last_date: pd.Timestamp
    residual_std: float

    def predict_dates(
        self, dates: pd.DatetimeIndex, level_adjustment: float = 0.0
    ) -> np.ndarray:
        offsets = (dates - self.origin).days.to_numpy(dtype=float)
        return (
            np.asarray(self.estimator.predict(_design_matrix(offsets)))
            + level_adjustment
        )

    def forecast(
        self,
        horizon: int,
        *,
        as_of: pd.Timestamp | None = None,
        level_adjustment: float = 0.0,
    ) -> list[ForecastPoint]:
        cutoff = self.last_date if as_of is None else pd.Timestamp(as_of)
        dates = pd.date_range(
            cutoff + pd.Timedelta(1, unit="D"), periods=horizon, freq="D"
        )
        predictions = self.predict_dates(dates, level_adjustment)
        interval = 1.96 * self.residual_std
        return [
            ForecastPoint(
                date.date().isoformat(),
                float(value),
                float(value - interval),
                float(value + interval),
                self.metadata.model_version,
            )
            for date, value in zip(dates, predictions, strict=True)
        ]


def _fit(frame: pd.DataFrame) -> tuple[LinearRegression, pd.Timestamp, float]:
    ordered = frame.sort_values("date")
    origin = pd.Timestamp(ordered["date"].iloc[0])
    offsets = (pd.to_datetime(ordered["date"]) - origin).dt.days.to_numpy(dtype=float)
    estimator = LinearRegression().fit(
        _design_matrix(offsets), ordered["net_cash_flow"]
    )
    residuals = ordered["net_cash_flow"].to_numpy() - estimator.predict(
        _design_matrix(offsets)
    )
    return estimator, origin, float(np.std(residuals, ddof=1))


def chronological_backtest_split(
    data: pd.DataFrame, horizon: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(data) <= horizon:
        raise ValueError("Cash-flow history must be longer than the backtest horizon")
    ordered = data.sort_values("date").reset_index(drop=True)
    return ordered.iloc[:-horizon], ordered.iloc[-horizon:]


def train_cash_flow_model(
    data: pd.DataFrame,
    *,
    seed: int,
    horizon: int = 30,
    model_version: str = "cash-flow-v1",
) -> tuple[CashFlowModel, dict[str, float]]:
    ordered = data.sort_values("date").reset_index(drop=True)
    train, test = chronological_backtest_split(ordered, horizon)
    backtest_estimator, origin, _ = _fit(train)
    test_offsets = (pd.to_datetime(test["date"]) - origin).dt.days.to_numpy(dtype=float)
    predicted = backtest_estimator.predict(_design_matrix(test_offsets))
    metrics = regression_metrics(test["net_cash_flow"], predicted)
    estimator, origin, residual_std = _fit(ordered)
    metadata = make_metadata(
        pipeline="cash_flow_forecast",
        model_version=model_version,
        data=data,
        features=["date", "net_cash_flow"],
        seed=seed,
        config={
            "horizon": horizon,
            "algorithm": "harmonic_linear_regression_prophet_fallback",
        },
        metrics=metrics,
    )
    return CashFlowModel(
        estimator,
        metadata,
        origin,
        pd.Timestamp(ordered["date"].iloc[-1]),
        residual_std,
    ), metrics


def save_cash_flow_model(model: CashFlowModel, path: Path) -> None:
    state = {
        "estimator": model.estimator,
        "origin": model.origin,
        "last_date": model.last_date,
        "residual_std": model.residual_std,
    }
    save_artifact(path, state, model.metadata)


def load_cash_flow_model(path: Path) -> CashFlowModel:
    state, metadata = load_artifact(
        path, pipeline="cash_flow_forecast", expected_features=["date", "net_cash_flow"]
    )
    return CashFlowModel(
        state["estimator"],
        metadata,
        state["origin"],
        state["last_date"],
        state["residual_std"],
    )
