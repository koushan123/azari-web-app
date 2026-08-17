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

No accounting or monetary tables are part of Stage 2.
