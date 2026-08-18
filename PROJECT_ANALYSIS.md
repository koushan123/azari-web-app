# Project Analysis

## Audit date and baseline

The repository was inspected on 2026-08-17 before implementation began. It was
empty: there were no source files, dependency manifests, configuration files,
database definitions, tests, documentation, or Git metadata. Consequently,
there is no legacy implementation to migrate or preserve.

Available host tooling at audit time:

- Python 3.14.6 and Python 3.12
- Node.js 24.18.0
- npm is installed, but PowerShell blocks `npm.ps1`; `npm.cmd` can be used
- Docker 29.7.2 and Docker Compose v5.4.0; Docker Engine execution is verified

## Missing components at baseline

All requested capabilities were missing, including authentication/RBAC,
accounting entities, double-entry posting, invoices and payments, reports,
audit logs, the four ML pipelines, model registry, frontend, migrations,
synthetic data, tests, containers, and operational documentation.

## Recommended architecture

The application will be a modular monorepo:

```text
frontend/                 React + TypeScript + Vite
  src/
    components/           reusable UI
    layouts/              navigation and page shells
    pages/                route-level screens
    services/             typed HTTP access
    hooks/ types/ charts/
backend/                  FastAPI application
  app/
    api/routes/           transport and request authorization only
    core/                 settings, security, RBAC
    db/models/            SQLAlchemy persistence model
    schemas/              Pydantic API contracts
    repositories/         persistence queries
    services/             accounting and application rules
    ml/                   inference adapters and model registry
  alembic/                database migrations
  tests/                  API, service, security, and integration tests
ml/                       framework-independent ML training package
  preprocessing/ training/ evaluation/ inference/ models/
scripts/                  synthetic data and operational utilities
docs/                     architecture, database, ML, API, and setup docs
```

FastAPI routes will call application services; services own transaction
boundaries and business rules; repositories isolate database access. ML
training remains independent of the web process. Inference adapters load
versioned artifacts and record predictions in PostgreSQL. This prevents model
code from becoming coupled to HTTP or ORM concerns.

PostgreSQL is the primary database. SQLAlchemy types and constraints will avoid
vendor-specific behavior where practical to retain reasonable MySQL
portability. Monetary values use fixed-precision decimals, never floats.

## Domain and data design

The accounting core will use a journal header plus journal lines. Each posted
journal must have at least two lines and equal debit and credit totals. Draft
invoices do not affect the ledger; issuing and paying invoices create journal
entries through one posting service. Invoice payment allocation supports
partial payments and derives status from amount paid and due date.

The normalized model will include users, roles, permissions, parties
(customer/supplier specializations where useful), products, accounts, account
categories, journals, journal lines, invoices, invoice items, payments,
financial periods, audit events, ML model versions, predictions, feedback, and
cluster assignments. Soft deletion is limited to master data; ledger records
are immutable after posting and corrected with reversing entries.

## ML design

- Transaction classification: TF-IDF plus Multinomial Naive Bayes and linear
  SVM comparison. The selected calibrated pipeline returns category,
  confidence, and manual-review status.
- Payment-delay risk: Random Forest trained on features computed strictly as of
  the prediction timestamp. Permutation or impurity feature contributions are
  translated into concise explanations.
- Cash flow: Prophet when supported by the runtime; a deterministic statistical
  fallback will be documented if Prophet cannot support Python 3.14. Forecasts
  include intervals and are evaluated with chronological backtesting.
- Segmentation: standardized financial features plus K-Means. Candidate `k`
  values are evaluated with inertia and silhouette score; labels are inferred
  from centroid characteristics rather than cluster IDs.

Every pipeline implements train, evaluate, save, load, and predict operations.
Artifacts, feature schemas, seeds, metrics, dataset fingerprints, and model
versions are stored together. Synthetic demo records are explicitly marked and
generated with behavioral profiles and temporal patterns.

## Architectural risks and mitigations

- **Empty baseline / large scope:** deliver vertical, tested milestones rather
  than disconnected modules.
- **Python 3.14 dependency support:** containerize on Python 3.12 and pin tested
  dependency ranges; treat the newer host interpreter as optional.
- **Forecasting dependency weight:** keep Prophet behind an adapter and out of
  the request lifecycle.
- **Accounting correctness:** centralize posting, use database transactions and
  decimal arithmetic, and test balance/period/immutability invariants.
- **Data leakage:** produce time-aware feature snapshots and chronological
  train/test splits.
- **Insufficient real data:** use realistic, labeled synthetic profiles without
  presenting demo metrics as real-world performance.
- **Security:** fail configuration when secrets are absent, hash passwords with
  Argon2, use short-lived JWTs, enforce permissions in dependencies, constrain
  CORS, audit mutations, and never serialize sensitive fields.
- **Host port reservation (resolved):** Windows excludes TCP ports 5141-5240,
  including attempted frontend ports 5173 and 5174. The approved host port 4173
  is outside that range and the complete Compose stack is verified running.
- **Backend host port reservation (resolved):** Windows also excludes TCP ports
  7927-8026, including host port 8000. Compose publishes backend container port
  8000 on host port 8100; the container and its internal healthcheck continue to
  use port 8000.

## Assumptions

- One organization and one base currency are sufficient for the bachelor's
  prototype; identifiers and service boundaries will allow later tenancy.
- PostgreSQL 16 and Python 3.12 are the supported deployment targets.
- Accounting periods and timestamps are stored in UTC; display timezone is a
  user-facing concern.
- Tax rules are configurable data, not jurisdiction-specific tax compliance.
- The initial frontend targets modern evergreen browsers and desktop/tablet
  dashboard layouts.

## Implementation roadmap

1. **Foundation:** monorepo layout, validated settings, backend/frontend health
   path, containers, test/lint tooling, documentation skeleton.
2. **Persistence and identity:** SQLAlchemy model base, Alembic migration,
   users, roles, permissions, JWT authentication, audit service.
3. **Accounting vertical slice:** customers/suppliers/products/accounts,
   balanced journals, invoices, payment allocation, and service/API tests.
4. **Reports and dashboard API:** statements, receivables/payables, filters, and
   aggregates derived from persisted records.
5. **ML pipelines:** reproducible training/evaluation/artifacts for all four
   algorithms plus synthetic behavioral data.
6. **ML integration:** prediction/training endpoints, registry and feedback,
   permission checks, explanations, and persisted results.
7. **Frontend:** authenticated workflows, accounting screens, reports,
   operational dashboard, and dedicated AI dashboard.
8. **Hardening:** integration/e2e tests, Docker verification, security review,
   complete docs, and a reproducible demonstration run.

## First implementation milestone

Milestone 1 is complete when configuration fails safely without required
secrets, `/api/v1/health` returns a typed response, the React shell reads that
endpoint, backend tests pass, frontend type checking/build passes, and the
three-service Compose topology runs with both host endpoints reachable. No mock
accounting or hardcoded ML predictions are introduced during this milestone.

### Milestone 1 status

Implemented and verified: validated fail-fast configuration, versioned backend
health API, React connectivity shell, pinned dependencies and lockfile, backend
container, frontend Nginx container, PostgreSQL Compose service, documentation
skeleton, and quality-tool configuration. Backend tests/lint/type checks and the
frontend production build pass. Docker installation and Compose configuration
are verified. After adding context-specific Docker ignore rules, both images
build successfully and the backend health endpoint returns HTTP 200. Compose
correctly renders frontend host port 4173 targeting container port 80. The
Stage 1 backend mapping was 8000:8000; it was later adjusted during Stage 2 to
8100:8000 because Windows reserves host port 8000. The complete three-service
stack is running: PostgreSQL is healthy, the backend health endpoint returns
HTTP 200, and the frontend returns HTTP 200 at `http://localhost:4173`. Backend tests, Ruff,
strict mypy, and the frontend production build all pass. Stage 1 is **PASS**.
See `STAGE_1_VERIFICATION.md` for command-level evidence. At the Stage 1
checkpoint, Stage 2 had not begun.

## Stage 2 — Persistence and identity

### Implemented architecture

Stage 2 adds a synchronous SQLAlchemy 2 session foundation, typed UUID models,
Alembic migration authority, repositories, identity services, and thin FastAPI
routes. The schema contains users, roles, permissions, user-role links,
role-permission links, and append-oriented audit events. It deliberately adds no
accounting, reporting, or ML tables.

Passwords use Argon2id. JWT access tokens use the configured HMAC algorithm,
secret, and lifetime. Public registration is fixed to VIEWER and rejects extra
role input. Authorization resolves database permissions inherited across all
roles through centralized FastAPI dependencies. Registration and login
success/failure create audit events, while audit metadata rejects sensitive-key
payloads.

Compose runs Alembic and idempotent RBAC bootstrap as an explicit development
startup command; the backend image default starts only Uvicorn. Optional admin
bootstrap requires paired environment credentials and has no hardcoded default.

### Stage 2 status

Stage 2 is **PASS**. Verification completed on Python 3.12 and PostgreSQL 16:

- 25 backend tests passed with 94% application coverage;
- Ruff passed;
- strict mypy passed across 38 source files;
- frontend TypeScript/Vite production build passed;
- isolated PostgreSQL migration upgrade/downgrade/upgrade passed;
- PostgreSQL constraints, timezone-aware timestamps, RBAC bootstrap, and model
  schema alignment passed;
- registration, login, `/auth/me`, 401, 403, safe serialization, and audit
  persistence passed;
- final Compose rebuild has all three services running, PostgreSQL/backend
  healthy, backend HTTP 200 on host port 8100 (container port 8000), and
  frontend HTTP 200 on host port 4173.

Detailed implementation, security decisions, tests, and limitations are in
`STAGE_2_IMPLEMENTATION.md`. Stage 3 has not started.
