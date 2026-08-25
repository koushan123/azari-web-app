"""Point-in-time correct feature engineering for payment-delay prediction."""

from __future__ import annotations

import pandas as pd

PAYMENT_FEATURES = [
    "amount",
    "prior_invoice_count",
    "prior_average_amount",
    "prior_average_delay",
    "prior_late_rate",
    "prior_paid_amount",
    "prior_invoice_frequency",
    "prior_payment_frequency",
    "outstanding_at_prediction",
    "customer_tenure_days",
]


def build_payment_features(events: pd.DataFrame, delay_days: int = 7) -> pd.DataFrame:
    required = {
        "customer_id",
        "invoice_id",
        "invoice_date",
        "due_date",
        "payment_date",
        "amount",
    }
    missing = required.difference(events.columns)
    if missing:
        raise ValueError(f"Missing payment columns: {sorted(missing)}")
    ordered = events.copy()
    for column in ("invoice_date", "due_date", "payment_date"):
        ordered[column] = pd.to_datetime(ordered[column])
    ordered = ordered.sort_values(["invoice_date", "customer_id", "invoice_id"])
    rows: list[dict[str, object]] = []
    for customer_id, group in ordered.groupby("customer_id", sort=True):
        history: list[pd.Series] = []
        first_date = pd.Timestamp(group["invoice_date"].min())
        for _, current in group.iterrows():
            prediction_time = pd.Timestamp(current["invoice_date"])
            completed = [
                item
                for item in history
                if pd.Timestamp(item["payment_date"]) < prediction_time
            ]
            delays = [
                (
                    pd.Timestamp(item["payment_date"]) - pd.Timestamp(item["due_date"])
                ).days
                for item in completed
            ]
            outstanding = sum(
                float(item["amount"])
                for item in history
                if pd.Timestamp(item["payment_date"]) >= prediction_time
            )
            target_delay = (
                pd.Timestamp(current["payment_date"])
                - pd.Timestamp(current["due_date"])
            ).days
            tenure_months = max((prediction_time - first_date).days / 30.0, 1.0)
            rows.append(
                {
                    "customer_id": customer_id,
                    "invoice_id": current["invoice_id"],
                    "prediction_time": prediction_time,
                    "amount": float(current["amount"]),
                    "prior_invoice_count": len(history),
                    "prior_average_amount": (
                        sum(float(item["amount"]) for item in history) / len(history)
                        if history
                        else 0.0
                    ),
                    "prior_average_delay": sum(delays) / len(delays) if delays else 0.0,
                    "prior_late_rate": (
                        sum(value > delay_days for value in delays) / len(delays)
                        if delays
                        else 0.0
                    ),
                    "prior_paid_amount": sum(
                        float(item["amount"]) for item in completed
                    ),
                    "prior_invoice_frequency": len(history) / tenure_months,
                    "prior_payment_frequency": len(completed) / tenure_months,
                    "outstanding_at_prediction": outstanding,
                    "customer_tenure_days": (prediction_time - first_date).days,
                    "delayed": int(target_delay > delay_days),
                }
            )
            history.append(current)
    return pd.DataFrame(rows).sort_values("prediction_time").reset_index(drop=True)
