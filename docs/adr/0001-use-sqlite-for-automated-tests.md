---
status: accepted
date: 2026-09-09
---

# 1. Use SQLite in-memory for automated backend tests

## Context
Previously, running `pytest` in the backend loaded `core.settings`, which reads the `.env` file containing the PostgreSQL / Supabase `DATABASE_URL`. This created a risk of tests executing against or interacting with the remote production database.

## Decision
Automated backend tests will use an isolated SQLite in-memory database configured in `backend/core/settings_test.py` and referenced by `backend/pytest.ini` (`DJANGO_SETTINGS_MODULE = core.settings_test`). Production will continue to use PostgreSQL/Supabase.

## Benefits
- **Isolation & Security:** Prevents test runs from accidentally altering or reading production data.
- **Speed:** SQLite in-memory operates significantly faster than remote network database connections.
- **Reproducibility:** Tests execute in a clean environment with zero external dependencies.

## Consequences
SQLite does not perfectly replicate PostgreSQL-specific features or behavior.

## Alternatives Considered
- **Running full test suite on Supabase:** Rejected due to data corruption risks, network latency, and environment dependency.

## When to Reconsider
- When testing PostgreSQL-specific queries, complex concurrency features, critical database migrations, or proven SQL engine divergence.

## Future Evolution
- If necessary, introduce a small, isolated integration test suite using a local PostgreSQL container, never production.
