# Architecture

The system uses a React client, a versioned FastAPI REST API, PostgreSQL, and
offline scikit-learn/Prophet training pipelines. HTTP routes remain thin;
services enforce accounting rules and transactions; repositories isolate ORM
queries. The ML runtime consumes versioned artifacts through adapters and logs
predictions and corrections for later retraining.

Stage 3 request flow is:

```text
FastAPI route → authentication/RBAC dependency → service → repository
              → SQLAlchemy Session → PostgreSQL
```

Services own commits for identity transactions and create audit events in the
same transaction where practical. Repositories contain query mechanics. JWT and
Argon2 utilities are isolated in `core/`; database models never enter response
serialization without explicit safe Pydantic schemas. Permissions are resolved
through `user_roles` and `role_permissions`, avoiding scattered role-name checks.

`AccountingService` owns master-data validation and every ledger transaction.
Manual journals, invoice issuance, and payment posting all converge on one
posting validator. It verifies period/account state, two-line minimum,
positive one-sided lines, and debit/credit equality before changing a journal
to POSTED. Reversals create new opposite entries; posted entries have no update
or delete operation. Invoice/payment state and their journals commit together.

Stage 4 is a read-only reporting slice. `ReportingRepository` owns aggregate
SQL over existing journal, invoice, allocation, payment, account, and party
tables. `ReportingService` applies accounting normal-balance semantics,
historical as-of allocation logic, filters, and response composition. Reports
never create ledger state and never duplicate posting rules.

Compose performs development migration/bootstrap explicitly. The image default
does not mutate schema, and production deployment can run migrations as a
separate controlled job.

Detailed decisions and the delivery roadmap are in `PROJECT_ANALYSIS.md`.
