"""Write deterministic, explicitly synthetic Stage 5 datasets to CSV."""

from __future__ import annotations

import argparse
from pathlib import Path

from ml.synthetic import cash_flow_data, customer_data, payment_data, transaction_data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("ml/generated"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    datasets = {
        "transactions": transaction_data(args.seed),
        "payments": payment_data(args.seed),
        "cash_flow": cash_flow_data(args.seed),
        "customers": customer_data(args.seed),
    }
    for name, frame in datasets.items():
        path = args.output / f"{name}.csv"
        frame.to_csv(path, index=False)
        print(f"{name}: {len(frame)} synthetic rows -> {path}")


if __name__ == "__main__":
    main()
