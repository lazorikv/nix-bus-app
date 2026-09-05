---
name: new-endpoint
description: Add a new backend REST endpoint following this project's package-by-feature pattern (model, schema, service, routes, RBAC, tests). Use when adding or extending an API resource on the FastAPI backend.
---

# Add a backend endpoint

Each feature is one vertical slice under `app/modules/<feature>/`. Extend the
matching module, or add a new one. Do not put business logic in routes.

1. **Model** (`app/infrastructure/db/models/`) — SQLAlchemy model with
   constraints. Reuse the `TimestampMixin` for `created_at` / `updated_at`. Add
   CHECK constraints for domain invariants (e.g. non-negative quantities). Export
   it from the models `__init__.py`. Values from a fixed set are `StrEnum`.

2. **Schema** (`app/modules/<feature>/schemas.py`) — Pydantic v2 request/response
   models. Do input validation here (bounds, `Literal`/enums, required fields).
   Paginated lists return `app/core/pagination.py`'s `Page[T]`.

3. **Service** (`app/modules/<feature>/service.py`) — a class taking its session
   via `Annotated[Session, Depends(get_session)]`; it owns business logic and
   queries and raises domain exceptions from `app/core/exceptions.py` (never
   `HTTPException`). Anything touching seat counts must stay atomic: a single
   `UPDATE ... WHERE ... RETURNING`, never read-then-write. Never let `seats_left`
   go negative. Inject `SeatsService` for reservation/release.

4. **Routes** (`app/modules/<feature>/routes.py`) — thin HTTP layer: inject the
   service via `Annotated[Service, Depends()]`, call one method, return the
   result. Enforce RBAC with the dependencies in `app/core/deps.py`
   (`get_current_user`, `require_admin`). Public reads stay open; writes are
   role-gated per the brief. Export the service from the module `__init__.py`.

5. **Register** the module router in `app/router.py`'s `create_router()`.

6. **Tests** (`tests/`) — cover the happy path **and** permission enforcement
   (anonymous / user / admin) for every protected operation. Use the fixtures in
   `conftest.py` (`admin_headers`, `user_headers`, `sample_bus`, `sample_trip`).
   Write tests first for any real domain logic (TDD red → green).

Before the PR: run the `run-tests` skill, plus `ruff check .` and `mypy app`.
