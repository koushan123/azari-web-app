# Architecture

The system uses a React client, a versioned FastAPI REST API, PostgreSQL, and
offline scikit-learn/Prophet training pipelines. HTTP routes remain thin;
services enforce accounting rules and transactions; repositories isolate ORM
queries. The ML runtime consumes versioned artifacts through adapters and logs
predictions and corrections for later retraining.

Stage 2 request flow is:

```text
FastAPI route → authentication/RBAC dependency → service → repository
              → SQLAlchemy Session → PostgreSQL
```

Services own commits for identity transactions and create audit events in the
same transaction where practical. Repositories contain query mechanics. JWT and
Argon2 utilities are isolated in `core/`; database models never enter response
serialization without explicit safe Pydantic schemas. Permissions are resolved
through `user_roles` and `role_permissions`, avoiding scattered role-name checks.

Compose performs development migration/bootstrap explicitly. The image default
does not mutate schema, and production deployment can run migrations as a
separate controlled job.

Detailed decisions and the delivery roadmap are in `PROJECT_ANALYSIS.md`.
