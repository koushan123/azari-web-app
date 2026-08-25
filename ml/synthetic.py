"""Deterministic, noisy synthetic datasets for local ML development only."""

from __future__ import annotations

import numpy as np
import pandas as pd


def transaction_data(seed: int = 42, rows: int = 900) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    vocabulary = {
        "office_supplies": [
            "printer paper",
            "desk chair",
            "ink cartridge",
            "stationery",
        ],
        "travel": ["hotel booking", "airline ticket", "taxi fare", "train journey"],
        "utilities": [
            "electric bill",
            "internet service",
            "water charge",
            "mobile plan",
        ],
        "meals": ["client lunch", "team dinner", "coffee meeting", "catering order"],
        "software": [
            "cloud subscription",
            "software licence",
            "hosting renewal",
            "app plan",
        ],
    }
    merchants = ["north", "central", "prime", "metro", "acme", "global"]
    noise = ["monthly", "business", "invoice", "payment", "online", "local", "urgent"]
    records: list[dict[str, object]] = []
    labels = list(vocabulary)
    for index in range(rows):
        label = labels[index % len(labels)]
        phrase_label = label
        if rng.random() < 0.12:
            phrase_label = str(
                rng.choice([value for value in labels if value != label])
            )
        phrase = str(rng.choice(vocabulary[phrase_label]))
        words = [str(rng.choice(merchants)), phrase, str(rng.choice(noise))]
        if rng.random() < 0.18:
            other = str(rng.choice([value for value in labels if value != label]))
            words.append(str(rng.choice(vocabulary[other])).split()[0])
        records.append(
            {"description": " ".join(words), "category": label, "is_synthetic": True}
        )
    return pd.DataFrame(records)


def payment_data(
    seed: int = 42, customers: int = 100, invoices: int = 12
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records: list[dict[str, object]] = []
    base = pd.Timestamp("2023-01-01")
    for customer in range(customers):
        profile_delay = float(rng.choice([-4, 1, 8, 18], p=[0.2, 0.4, 0.25, 0.15]))
        base_amount = float(rng.uniform(150, 3500))
        for sequence in range(invoices):
            day_offset = int(sequence * 28 + int(rng.integers(0, 8)))
            invoice_date = base + pd.Timedelta(day_offset, unit="D")
            due_date = invoice_date + pd.Timedelta(30, unit="D")
            delay = round(profile_delay + rng.normal(0, 6))
            payment_date = due_date + pd.Timedelta(delay, unit="D")
            amount = max(25.0, base_amount * float(rng.lognormal(0, 0.28)))
            records.append(
                {
                    "customer_id": f"C{customer:04d}",
                    "invoice_id": f"I{customer:04d}-{sequence:02d}",
                    "invoice_date": invoice_date,
                    "due_date": due_date,
                    "payment_date": payment_date,
                    "amount": round(amount, 2),
                    "is_synthetic": True,
                }
            )
    return (
        pd.DataFrame(records)
        .sort_values(["invoice_date", "customer_id"])
        .reset_index(drop=True)
    )


def cash_flow_data(seed: int = 42, days: int = 500) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-01-01", periods=days, freq="D")
    t = np.arange(days)
    values = (
        850
        + 1.15 * t
        + 210 * np.sin(2 * np.pi * t / 7)
        + 130 * np.cos(2 * np.pi * t / 30.5)
        + rng.normal(0, 95, days)
    )
    return pd.DataFrame(
        {"date": dates, "net_cash_flow": values.round(2), "is_synthetic": True}
    )


def customer_data(seed: int = 42, rows: int = 260) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    profiles = [(9, 900, 2, 0.03), (24, 2400, 9, 0.12), (42, 5200, 20, 0.28)]
    records: list[dict[str, object]] = []
    for index in range(rows):
        count, average, delay, outstanding_rate = profiles[index % len(profiles)]
        invoice_count = max(2, int(rng.normal(count, count * 0.22)))
        avg_amount = max(50, float(rng.normal(average, average * 0.28)))
        total = invoice_count * avg_amount
        outstanding = max(0, total * float(rng.normal(outstanding_rate, 0.07)))
        records.append(
            {
                "customer_id": f"C{index:04d}",
                "invoice_count": invoice_count,
                "total_invoice_amount": round(total, 2),
                "avg_invoice_amount": round(avg_amount, 2),
                "total_payment_amount": round(max(0, total - outstanding), 2),
                "avg_delay_days": round(max(-5, float(rng.normal(delay, 5))), 2),
                "outstanding_balance": round(outstanding, 2),
                "payment_frequency": round(
                    invoice_count / float(rng.uniform(8, 16)), 3
                ),
                "is_synthetic": True,
            }
        )
    return pd.DataFrame(records)
