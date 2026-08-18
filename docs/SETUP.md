# Setup

## Docker development

Install Docker Desktop (or Docker Engine with Compose), copy `.env.example` to
`.env`, replace all placeholder credentials, and run:

```shell
docker compose up --build
```

The Compose backend command waits for healthy PostgreSQL, runs
`alembic upgrade head`, idempotently seeds canonical roles/permissions, and then
starts Uvicorn. The image default itself only starts Uvicorn so migration policy
can be controlled independently outside the development Compose environment.

## Backend without Docker

Python 3.12 is the supported runtime. From the repository root:

```shell
python -m venv .venv
.venv/Scripts/pip install -e "backend[dev]"
copy .env.example .env
.venv/Scripts/uvicorn backend.app.main:app --reload
```

Adjust `DATABASE_URL` for a reachable PostgreSQL instance. Apply migrations and
bootstrap RBAC before starting the local API:

```shell
.venv/Scripts/alembic -c backend/alembic.ini upgrade head
.venv/Scripts/python -m backend.app.db.bootstrap
```

Run tests with:

```shell
.venv/Scripts/pytest backend/tests
```

## Frontend without Docker

From `frontend/`, run `npm.cmd install` and `npm.cmd run dev` on Windows. The
frontend reads `VITE_API_URL`; its default is `http://localhost:8100/api/v1`.

## Required secrets

`JWT_SECRET` must be a random value at least 32 characters long. Never use the
example placeholder outside initial local setup and never commit `.env`.

`BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` are optional and must be
set together. The password must be 12–128 characters. Bootstrap is idempotent
and never overwrites an existing user. Omit both in production and provision
administrators through a controlled operational process.

## Clean database

On a clean PostgreSQL database, run the Alembic and bootstrap commands above.
Never use `Base.metadata.create_all()` for application deployment; it is used
only by isolated unit-test fixtures.
