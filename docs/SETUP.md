# Setup

## Docker development

Install Docker Desktop (or Docker Engine with Compose), copy `.env.example` to
`.env`, replace all placeholder credentials, and run:

```shell
docker compose up --build
```

## Backend without Docker

Python 3.12 is the supported runtime. From the repository root:

```shell
python -m venv .venv
.venv/Scripts/pip install -e "backend[dev]"
copy .env.example .env
.venv/Scripts/uvicorn backend.app.main:app --reload
```

Adjust `DATABASE_URL` for a reachable PostgreSQL instance. Run tests with:

```shell
.venv/Scripts/pytest backend/tests
```

## Frontend without Docker

From `frontend/`, run `npm.cmd install` and `npm.cmd run dev` on Windows. The
frontend reads `VITE_API_URL`; its default is `http://localhost:8000/api/v1`.

## Required secrets

`JWT_SECRET` must be a random value at least 32 characters long. Never use the
example placeholder outside initial local setup and never commit `.env`.

