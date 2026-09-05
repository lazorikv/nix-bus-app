# Bus Management

A web application for a bus-transportation company: manage cities, buses, trips, and orders, and let users search and book tickets. The interesting complexity lives in the domain logic — atomic seat reservation under concurrency, an idempotent payment webhook, and role-based access control (RBAC).

## Stack and why

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | **FastAPI + SQLAlchemy 2.0 + Pydantic v2** | fast async framework, type-safe schemas, mature ORM |
| Database | **PostgreSQL 16** | needs transactional `UPDATE ... WHERE ... RETURNING` for atomic seat reservation |
| Photo storage | **MinIO** (S3-compatible) | same S3 API as AWS S3, but runs locally with one command and no cloud (see [S3 wiring](#s3--minio-wiring)) |
| Auth | **JWT** (python-jose) + bcrypt | stateless authentication, role enforcement on every protected endpoint |
| PDF tickets | **ReportLab** | ticket generated when an order is paid |
| Frontend | **React + Vite + TypeScript + React Router** | SPA with role-aware rendering and a type-safe API client |
| Tests | **pytest + pytest-cov** | target ≥ 80% coverage on the domain core |
| Lint/types | **ruff** (lint + format), **mypy**, **eslint** | |
| Orchestration | **docker-compose** | app + Postgres + MinIO in one command |
| CI | **GitHub Actions** | lint + type-check + tests on every PR |

## Quick start (docker-compose)

Brings up the backend, PostgreSQL, MinIO, and frontend with a single command:

```bash
docker compose up --build
```

Once running:

- Frontend — http://localhost:5173
- Backend API + Swagger — http://localhost:8000/docs
- Health check — http://localhost:8000/health
- MinIO console — http://localhost:9001 (login/password `minioadmin` / `minioadmin`)

On startup the backend automatically creates the tables, the `bus-photos` bucket, and the first
admin user (`admin@busapp.com` / `admin12345`, configured via `FIRST_ADMIN_EMAIL` /
`FIRST_ADMIN_PASSWORD`).

## Local development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # adjust variables if needed
# requires a running Postgres (e.g. `docker compose up db`)
python -m app.init_db         # create tables + bucket + admin
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173, expects the API at VITE_API_URL (default http://localhost:8000)
```

## Testing

Tests require PostgreSQL (not SQLite — they rely on server-side `UPDATE ... RETURNING` and
`TRUNCATE`). The easiest path is to start the test database from docker-compose and point the
tests at it via `TEST_DATABASE_URL`:

```bash
docker compose up -d db       # Postgres on localhost:5432
cd backend
pip install -e ".[dev]"
TEST_DATABASE_URL=postgresql+psycopg2://bus:bus@localhost:5432/bus_test \
  pytest --cov --cov-report=term-missing --cov-fail-under=80
```

Object storage (MinIO) is mocked in tests — no calls reach it.

Key domain tests:

- `tests/test_seats_concurrency.py` — concurrent booking: `seats_left` never goes negative.
- `tests/test_payment.py`, `tests/test_payment_api.py` — webhook idempotency and seat restoration on `failed`.
- `tests/test_orders.py` — order status transitions (pending → paid / failed) and RBAC.

Lint and types:

```bash
cd backend && ruff check . && ruff format --check . && mypy app
cd frontend && npm run lint && npm run build
```

## S3 / MinIO wiring

The brief requires photo upload to S3 and retrieval via presigned URL. Instead of AWS S3 this
project uses **MinIO** — it speaks the same S3 API, so the same `boto3` client works against both;
only the endpoint and credentials change. Implementation lives in `backend/app/storage.py`:

- **Two clients.** Inside docker the backend reaches MinIO over the internal address
  `S3_ENDPOINT_URL` (`http://minio:9000`). Presigned URLs, however, are opened by the user's
  browser, so they are signed with a separate client using the public `S3_PUBLIC_ENDPOINT_URL`
  (`http://localhost:9000`). Otherwise the signature would not match the host the browser sees.
- **Upload** (admin creates/updates a bus): file type is validated (JPEG/PNG), the image is stored
  in bucket `S3_BUCKET`, and a thumbnail is generated (Pillow) — see `app/services/photos.py`.
- **Retrieval**: the client receives a time-limited presigned GET URL instead of a public link
  (`PRESIGNED_URL_EXPIRE_SECONDS`, default 1 hour).
- **The bucket** is created idempotently on startup (`ensure_bucket()` in `app/init_db.py`).

Environment variables — see `backend/.env.example`.

## API overview

| Resource | Operations |
|----------|-----------|
| Auth | register, login, `GET /auth/me` |
| Cities | CRUD (writes admin-only, reads public) |
| Buses | CRUD + photo upload/retrieval (admin-only) |
| Trips | CRUD + search (origin/destination/date, filter by price/time/seats, sort, pagination) |
| Orders | create (incl. anonymous, `user_id = NULL`), list own (admin: all), get |
| Payment | webhook `(order_id, success)` — idempotent, restores seats on failure |
| Meta | `GET /health` |

Full interactive documentation lives at `/docs` (Swagger UI).

### Payment webhook auth

`POST /payment/webhook` authenticates the caller with a shared secret sent in the
`X-Webhook-Secret` header (`PAYMENT_WEBHOOK_SECRET`, compared in constant time); a
request with a missing or wrong secret is rejected with `401` before any status
change, so an order can't be flipped to `paid`/`failed` by an unauthenticated caller.
The `POST /payment/simulate/{order_id}` mock-gateway trigger used by the booking
flow is a development helper — it returns `404` when `ENVIRONMENT=production`.

## Observability

Structured logging (`app/logging_config.py`): request events (`request.completed`), errors
(`request.error`, `request.unhandled_exception`), and business events (order creation, payment,
seat reservation). Every request is assigned an `X-Request-ID`.

## CI

`.github/workflows/ci.yml` runs on every pull request and push to `main`:

- **backend**: `ruff check` + `ruff format --check` + `mypy app` + `pytest --cov --cov-fail-under=80`
  (Postgres runs as a service container);
- **frontend**: `npm run lint` + `npm run build` (tsc + vite).

No cloud deployment — per the assignment.
