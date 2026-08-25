# Machine Learning

Stage 5 is an offline, framework-independent package. It imports neither
FastAPI nor SQLAlchemy. Normal backend startup loads no model and performs no
training; Stage 6 will own web/database integration.

## Pipelines

- Transaction classification compares TF-IDF + Multinomial Naive Bayes with
  TF-IDF + calibrated linear SVM on a seeded stratified 75/25 split. Macro F1,
  then accuracy, selects the saved complete pipeline. Inference returns the
  category, calibrated probability, configured manual-review decision, and
  model version.
- Payment-delay risk predicts whether an invoice is paid more than seven days
  after its due date. Features include current amount and, as of invoice time,
  prior amounts, delays, late rate, paid amount, invoice/payment frequencies,
  outstanding balance, and tenure. A seeded Random Forest uses chronological
  70/15/15 train/validation/test partitions. Its contribution values are
  model-level importance heuristics, not causal explanations.
- Cash-flow forecasting uses daily frequency, a 30-day horizon, all earlier
  observations as the expanding training window, and a final chronological
  holdout. The deterministic fallback is linear trend plus weekly, monthly,
  and annual harmonic terms; intervals are residual-based 95% intervals.
  Prophet is intentionally omitted because its compiled dependency stack is
  unnecessary for the supported Python 3.12 runtime and the prompt permits a
  documented deterministic statistical fallback.
- Segmentation fits `StandardScaler` on an 80% seeded training partition, then
  compares K-Means k=2..6 by inertia and silhouette. Maximum silhouette selects
  k. Descriptions are generated from inverse-scaled centroid value, payment
  delay, and outstanding-balance characteristics; cluster IDs have no inherent
  meaning.

## Synthetic data

`scripts/generate_ml_data.py --seed 42` writes explicitly labeled CSVs under
ignored `ml/generated/`: 900 noisy/overlapping transaction descriptions, 1,200
invoices from 100 payment profiles over time, 500 daily cash-flow observations
with trend/seasonality/noise, and 260 overlapping customer profiles. These are
demonstration datasets only. Their metrics do not estimate real-world accuracy,
fairness, calibration, or business value.

## Training and artifacts

Install `backend[dev,ml]`, then run `python scripts/train_ml.py`. Each model is
saved at `ml/models/<pipeline>/<model-version>/` as `model.joblib` plus
`metadata.json`. The metadata records schema/model versions, UTC training time,
SHA-256 dataset fingerprint, feature schema, seed, configuration, metrics,
dependency versions, and the synthetic-data flag. Loaders reject the wrong
pipeline or artifact schema. Complete preprocessors are persisted with models.

Python inference uses the loaders in `ml.inference`, for example:

```python
from pathlib import Path
from ml.inference.transaction import load_transaction_model

model = load_transaction_model(Path("ml/models/transaction/transaction-v1"))
prediction = model.predict("metro hotel booking business")
```

## Leakage and reproducibility

The text vectorizer is inside the candidate pipeline and sees training rows
only. Payment snapshots use only earlier invoices and payments completed before
the prediction timestamp. Cash-flow evaluation sorts by date and never
shuffles. The segmentation scaler learns only from the training partition.
Tests mutate future outcomes, use test-only vocabulary, assert chronological
boundaries/scaler statistics, repeat seeded training, and compare save/load
predictions.

## Demo metrics and limitations

Seed-42 synthetic metrics are: transaction accuracy 0.9244/macro F1 0.9247;
payment-risk test accuracy 0.8167/F1 0.6024/ROC AUC 0.8192; cash-flow MAE
70.4534/RMSE 93.3948; segmentation silhouette 0.5880. These are
**DEMO/SYNTHETIC METRICS, not real-world model performance**. Before production,
models require representative data, calibrated business thresholds, drift and
bias monitoring, forecast diagnostics, security review, and human validation.
