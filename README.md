# Azari Intelligent Accounting

An academic, production-oriented accounting application integrating
double-entry bookkeeping with transaction classification, payment-delay risk,
cash-flow forecasting, and customer/supplier segmentation.

The repository is being implemented in verified milestones. The current
milestone establishes the application foundation and health path. See
[PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md) for the audit, architecture, risks,
and roadmap.

## Quick start

1. Copy `.env.example` to `.env` and replace every `change-me` value.
2. With Docker installed, run `docker compose up --build`.
3. Open the frontend at `http://localhost:4173` and API documentation at
   `http://localhost:8000/docs`.

Local backend and frontend setup is documented in [docs/SETUP.md](docs/SETUP.md).
