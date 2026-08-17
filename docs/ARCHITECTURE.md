# Architecture

The system uses a React client, a versioned FastAPI REST API, PostgreSQL, and
offline scikit-learn/Prophet training pipelines. HTTP routes remain thin;
services enforce accounting rules and transactions; repositories isolate ORM
queries. The ML runtime consumes versioned artifacts through adapters and logs
predictions and corrections for later retraining.

Detailed decisions and the delivery roadmap are in `PROJECT_ANALYSIS.md`.

