---
name: new-endpoint
description: Add a new backend REST endpoint following this project's layered pattern (model, schema, service, router, RBAC, tests). Use when adding or extending an API resource on the FastAPI backend.
---

# Add a backend endpoint

Follow the existing layering — do not put business logic in routers.

1. **Model** (`app/models/`) — SQLAlchemy model with constraints. Reuse the
   `TimestampMixin` for `created_at` / `updated_at`. Add CHECK constraints for
   domain invariants (e.g. non-negative quantities).

2. **Schema** (`app/schemas/`) — Pydantic v2 request/response models. Do input
   validation here (bounds, enums, required fields).

3. **Service** (`app/services/`) — business logic. Anything touching seat counts
   must stay atomic: a single `UPDATE ... WHERE ... RETURNING`, never
   read-then-write. Never let `seats_left` go negative.

4. **Router** (`app/routers/`) — thin HTTP layer. Enforce RBAC with the
   dependencies in `app/core/deps.py` (`get_current_user`, admin guard). Public
   reads stay open; writes are role-gated per the brief.

5. **Register** the router in `app/main.py` (`app.include_router(...)`).

6. **Tests** (`tests/`) — cover the happy path **and** permission enforcement
   (anonymous / user / admin) for every protected operation. Use the fixtures in
   `conftest.py` (`admin_headers`, `user_headers`, `sample_bus`, `sample_trip`).
   Write tests first for any real domain logic (TDD red → green).

Before the PR: run the `run-tests` skill, plus `ruff check .` and `mypy app`.
