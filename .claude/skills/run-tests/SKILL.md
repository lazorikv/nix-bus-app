---
name: run-tests
description: Run the backend test suite with coverage against the Postgres test DB. Use whenever the user wants to run tests, check coverage, or verify the backend before a PR.
---

# Run the backend tests

Tests require **PostgreSQL** (not SQLite) — the domain relies on server-side
`UPDATE ... RETURNING` and `TRUNCATE`. Object storage is mocked in `conftest.py`.

1. Ensure the test database is up:

```bash
docker compose up -d db
```

2. From `backend/` (inside the venv), run the suite with the coverage gate:

```bash
TEST_DATABASE_URL=postgresql+psycopg2://bus:bus@localhost:5433/bus_test \
  pytest --cov --cov-report=term-missing --cov-fail-under=80
```

If the compose DB is on `localhost:5432`, use that port instead. The
`--cov-fail-under=80` gate must stay green — if coverage drops, add real tests
for the uncovered behavior rather than lowering the bar.

Also run lint and types before opening a PR:

```bash
ruff check . && ruff format --check . && mypy app
```
