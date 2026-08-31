# hub-api

Python3/Quart control-plane service scaffold -- Task 0.5 of
[docs/plans/2026-08-31-hubapi-node-to-quart-migration.md](../docs/plans/2026-08-31-hubapi-node-to-quart-migration.md)
(M0 Foundation). This is the app skeleton the 55 Node hub_module /
marketplace_module controllers get ported into, phase by phase (M1..M9).
No business logic lives here yet -- one example blueprint
(`blueprints/platform.py`) proves the port pattern every future
controller copies.

## Layout

```
hub_api/
  app.py              Quart app factory + hypercorn entry point
  config.py            env-driven HubAPIConfig (@dataclass(slots=True, frozen=True))
  blueprints/
    __init__.py         register_blueprints(app) -- mounts v1 + v2 routers
    platform.py          example v2 blueprint: tenant -> scope -> DTO chain
  routers/
    v1.py                frozen /api/v1 (matches admin/hub_module/frontend's api.js contract)
    v2.py                additive /api/v2/{module}/{surface}/{app_bundle}/{target}
  openapi/
    spec_builder.py       hand-curated public login-only OpenAPI document
    routes.py             /openapi/v1-public.json (public) + /openapi/v1.json (protected, generated)
  tests/                 21 tests: app factory, health, platform blueprint, OpenAPI split
  requirements.in/.txt   hash-pinned direct deps (flask_core installed separately, see Dockerfile)
  Dockerfile             multi-stage, rootless, hypercorn CMD
```

## Running locally

```bash
uv venv -p 3.13 .venv && source .venv/bin/activate
uv pip install --require-hashes -r requirements.txt
uv pip install -e ../libs/flask_core   # local dev only -- Dockerfile pip-installs it non-editable
python3 app.py                          # or: hypercorn app:app --bind 0.0.0.0:8204
```

## Testing

```bash
uv pip install pytest pytest-asyncio mypy ruff
python3 -m pytest tests/ -v
ruff check . && ruff format --check .
python3 -m mypy .
```

All 21 tests use `sqlite:memory` (pydal) -- no external Postgres dependency.

## OpenAPI (two documents, per backend.md)

- `GET /openapi/v1-public.json` -- unauthenticated, exactly one path (`POST /api/v1/auth/login`).
- `GET /openapi/v1.json` -- the full, quart-schema-generated document, behind
  the same `tenant_middleware` + `require_scope("platform:read")` chain as
  any other protected route. The default `quart-schema` doc routes
  (`/openapi.json`, `/docs`) are disabled in `app.py` -- they are
  unauthenticated by default and would otherwise expose the whole surface.

## API versions

- `/api/v1/*` -- frozen, ported 1:1 from the Node contract. Only a `POST
  /auth/login` 501 placeholder exists today (M1 lands the real OAuth flow).
- `/api/v2/{module}/{surface}/{app_bundle}/{target}` -- additive,
  bundle-oriented. `blueprints/platform.py` is mounted at
  `/api/v2/core/platform/default/*` as the one worked example.

## Known gaps (tracked, not fixed here)

- `libs/flask_core` ships no `py.typed` marker and `tenant_middleware`/
  `require_scope`'s inner wrappers are unannotated -- every consumer sees
  mypy `--strict`'s `untyped-decorator`; worked around here with scoped,
  documented `# type: ignore[untyped-decorator]` (see `blueprints/platform.py`,
  `openapi/routes.py`).
- `AsyncDAL.close_async()` (`libs/flask_core/flask_core/database.py`)
  closes the underlying pydal `DAL` from a different thread than created
  it, which pydal's thread-local bookkeeping rejects. `app.py`'s shutdown
  hook catches and logs this rather than crashing the ASGI lifespan
  (matching `services/core-community/app.py`'s existing pattern).
- gRPC (backend.md's mandatory service-to-service transport) is not wired
  in this scaffold -- REST + MCP only. Follow-up, not blocking M1.
