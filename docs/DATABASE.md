# Database

PostgreSQL 16 is the primary store. SQLAlchemy 2 typed mappings use one
synchronous session strategy and Alembic is the schema authority.

Stage 2 tables:

- `users`: UUID key, normalized unique email, Argon2 hash, names, active flag,
  timezone-aware creation/update/last-login timestamps;
- `roles` and `permissions`: UUID keys and unique stable names;
- `user_roles` and `role_permissions`: composite primary keys preventing
  duplicate assignments, with cascading link cleanup;
- `audit_events`: UUID key, optional actor with `ON DELETE SET NULL`, action,
  resource identity, success flag, timezone-aware occurrence, and JSON metadata.

User/role and role/permission link rows use `ON DELETE CASCADE`; audit history
survives user deletion through `ON DELETE SET NULL`. There is no audit mutation
API. The initial migration is `20260817_0001`; upgrade and downgrade are both
verified on an isolated PostgreSQL database. Alembic drift checking reports no
difference between mappings and the migrated schema.

Stage 3 migration `cd6670d77e70` adds:

- `parties`, `products`, `account_categories`, `accounts`, and
  `financial_periods` master data;
- `journal_entries` and `journal_lines` for the immutable posted ledger;
- `invoices` and `invoice_items` for receivables;
- `payments` and `payment_allocations` for settlement.

Money uses `NUMERIC(18,2)` and quantities use `NUMERIC(18,4)`. Named checks
enforce valid dates/statuses, positive quantities and allocations,
non-negative totals, and exactly one positive debit/credit side per line.
Unique constraints cover business identifiers and allocation pairs. Cross-row
balance, period overlap, lifecycle, and allocation limits remain service rules.
The Stage 3 migration was verified upgrade/downgrade/upgrade on isolated
PostgreSQL, followed by a zero-drift Alembic check.

Stage 4 adds no tables. Index-only migration `20260818_0002` adds composite
indexes for journal status/date, invoice customer/issue and status/due filters,
payment party/date and status/date filters, and allocation invoice lookup.
Financial statements include POSTED journals only.
Historical receivables sum POSTED allocations whose payment date is on or
before the requested `as_of` date rather than using the invoice's current paid
total.
