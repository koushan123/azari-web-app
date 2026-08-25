"""Train all Stage 5 models from deterministic synthetic development data."""

from __future__ import annotations

import argparse
from pathlib import Path

from ml.config import MLConfig
from ml.synthetic import cash_flow_data, customer_data, payment_data, transaction_data
from ml.training.cash_flow import save_cash_flow_model, train_cash_flow_model
from ml.training.payment_risk import save_payment_risk_model, train_payment_risk_model
from ml.training.segmentation import save_segmentation_model, train_segmentation_model
from ml.training.transaction import save_transaction_model, train_transaction_model


def train_all(output: Path, config: MLConfig) -> dict[str, dict[str, float]]:
    transaction, comparisons = train_transaction_model(
        transaction_data(config.random_seed), seed=config.random_seed,
        confidence_threshold=config.confidence_threshold,
    )
    save_transaction_model(transaction, output / "transaction" / transaction.metadata.model_version)

    risk, risk_metrics, _ = train_payment_risk_model(
        payment_data(config.random_seed), seed=config.random_seed,
        delay_days=config.risk_delay_days,
    )
    save_payment_risk_model(risk, output / "payment-risk" / risk.metadata.model_version)

    forecast, forecast_metrics = train_cash_flow_model(
        cash_flow_data(config.random_seed), seed=config.random_seed,
        horizon=config.forecast_horizon,
    )
    save_cash_flow_model(forecast, output / "cash-flow" / forecast.metadata.model_version)

    segments, segment_metrics = train_segmentation_model(
        customer_data(config.random_seed), seed=config.random_seed,
    )
    save_segmentation_model(segments, output / "segmentation" / segments.metadata.model_version)
    return {
        "transaction": comparisons[transaction.metadata.config["selected_model"]],
        "payment_risk": risk_metrics,
        "cash_flow": forecast_metrics,
        "segmentation": segment_metrics[int(segments.metadata.metrics["selected_k"])],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("ml/models"))
    args = parser.parse_args()
    for name, metrics in train_all(args.output, MLConfig.from_env()).items():
        formatted = ", ".join(f"{key}={value:.4f}" for key, value in metrics.items())
        print(f"{name}: {formatted}")


if __name__ == "__main__":
    main()

