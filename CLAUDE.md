# CLAUDE.md

Project conventions and commands for AI-assisted work on this repo. Keep changes consistent with what is described here.

## What this is

Full-stack "Bus Management" app: FastAPI backend + React/Vite/TypeScript frontend, PostgreSQL, MinIO (S3-compatible) for bus photos. The domain core is atomic seat reservation under concurrency, an idempotent payment webhook, and role-based access control (RBAC). See `README.md` for the full stack rationale and the project brief for the Definition of Done.

## Layout

- `backend/` — FastAPI app (`app/`), tests (`tests/`), `pyproject.toml`.
  - `app/models/` SQLAlchemy models · `app/schemas/` Pydantic schemas · `app/routers/` API endpoints · `app/services/` domain logic (seats, payment, photos, tickets) · `app/core/` security & deps · `app/storage.py` MinIO/S3 wrapper.
- `frontend/` — React SPA (`src/pages`, `src/components`, `src/api`, `src/auth`).
- `docker-compose.yml` — app + Postgres + MinIO.
- `.github/workflows/` — CI (lint, type-check, tests) and AI code review.

## Commands

Backend (run from `backend/`, inside the venv):

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .        # lint + format
mypy app                                     # type-check
python -m app.init_db                        # create tables + bucket + admin
uvicorn app.main:app --reload                # run API
TEST_DATABASE_URL=postgresql+psycopg2://bus:bus@localhost:5433/bus_test \
  pytest --cov --cov-report=term-missing --cov-fail-under=80
```

Frontend (run from `frontend/`):

```bash
npm install
npm run lint
npm run build        # tsc + vite build (also the type-check gate)
npm run dev
```

Full stack:

```bash
docker compose up --build
```

## Conventions

- **Tests require PostgreSQL**, not SQLite — the domain relies on server-side `UPDATE ... RETURNING` and `TRUNCATE`. Never switch tests to SQLite. Object storage is mocked in tests (see `tests/conftest.py`); do not hit real MinIO from tests.
- **TDD for domain logic.** Any change to seat reservation, the payment webhook, or order-status transitions is written test-first (red → green). Do not backfill tests after the fact to satisfy the coverage gate.
- **Coverage gate is 80%** (`--cov-fail-under=80`). Keep it green; if it drops, add real tests for the uncovered behavior rather than lowering the bar.
- **RBAC on every protected endpoint.** admin / user / anonymous — enforce with the dependencies in `app/core/deps.py`. Cover permission enforcement in tests.
- **Seat reservation must stay atomic** — a single `UPDATE ... WHERE seats_left >= n RETURNING`, never a read-then-write. `seats_left` must never go negative; the concurrency test in `tests/test_seats_concurrency.py` proves it.
- **Payment webhook is idempotent** and restores seats on failure. A repeated webhook for the same order must not double-apply.
- **Lint/format/types must pass** before a PR: `ruff check`, `ruff format --check`, `mypy app`, `npm run lint`, `npm run build`.
- **Never commit** `.env`, secrets, or the project brief PDFs (`*.pdf` is gitignored).

## Delivery workflow

Work ships through pull requests, not direct pushes to `main`:

1. Branch → implement (test-first for domain logic).
2. Run lint, types, and tests locally; review your own diff before pushing.
3. Open a PR — CI and the AI review workflow run on the diff.
4. Address every review comment (accept or reject with a reason), then merge behind the human gate.
