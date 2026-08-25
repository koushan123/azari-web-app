"""Configuration for offline ML workflows."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class MLConfig:
    random_seed: int = 42
    confidence_threshold: float = 0.65
    risk_delay_days: int = 7
    forecast_horizon: int = 30

    @classmethod
    def from_env(cls) -> MLConfig:
        return cls(
            random_seed=int(os.getenv("ML_RANDOM_SEED", "42")),
            confidence_threshold=float(os.getenv("ML_CONFIDENCE_THRESHOLD", "0.65")),
            risk_delay_days=int(os.getenv("ML_RISK_DELAY_DAYS", "7")),
            forecast_horizon=int(os.getenv("ML_FORECAST_HORIZON", "30")),
        )
