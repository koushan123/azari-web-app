# Azari Intelligent Accounting

An academic, production-oriented accounting application integrating
double-entry bookkeeping with transaction classification, payment-delay risk,
cash-flow forecasting, and customer/supplier segmentation.

The repository is being implemented in verified milestones. Stage 1 provides
the runnable three-service foundation; Stage 2 adds PostgreSQL persistence,
identity, JWT authentication, database-backed RBAC, and security audit events. See
[PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md) for the audit, architecture, risks,
and roadmap.

## Quick start

1. Copy `.env.example` to `.env` and replace every `change-me` value.
2. With Docker installed, run `docker compose up --build`.
3. Open the frontend at `http://localhost:4173` and API documentation at
   `http://localhost:8100/docs`.

Local backend and frontend setup is documented in [docs/SETUP.md](docs/SETUP.md).

## Stage 2 identity API

- `POST /api/v1/auth/register` creates a normalized, Argon2-hashed VIEWER account.
- `POST /api/v1/auth/login` returns a short-lived bearer access token.
- `GET /api/v1/auth/me` returns the authenticated user without password data.
- `GET /api/v1/users` requires the database permission `users:read`.

Compose applies Alembic migrations and idempotently seeds roles/permissions
before starting the development API. It never creates an administrator unless
both optional bootstrap environment variables are explicitly set.
