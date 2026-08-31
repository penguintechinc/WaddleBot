# hub-api

Python3/Quart control-plane service scaffold -- Task 0.5 of
[docs/plans/2026-08-31-hubapi-node-to-quart-migration.md](../docs/plans/2026-08-31-hubapi-node-to-quart-migration.md)
(M0 Foundation). This is the app skeleton the 55 Node hub_module /
marketplace_module controllers get ported into, phase by phase (M1..M9).
No business logic lives here yet -- one example blueprint
(`blueprints/v2/platform.py`) proves the port pattern every future
controller copies.

## Layout

```
hub_api/
  app.py              Quart app factory + hypercorn entry point
  config.py            env-driven HubAPIConfig (@dataclass(slots=True, frozen=True))
  blueprints/
    __init__.py         register_blueprints(app) -- mounts v1 + v2 routers
    v1/
      auth.py             v1 `auth` group: M1 login stub, exposes BLUEPRINTS
    v2/
      platform.py          example v2 group: tenant -> scope -> DTO chain, exposes BLUEPRINTS
  routers/
    v1.py                frozen /api/v1 -- AUTO-DISCOVERS blueprints/v1/*, never edited per port
    v2.py                additive /api/v2/{module}/{surface}/{app_bundle}/{target} -- same, blueprints/v2/*
    _discovery.py         shared pkgutil-based discover_blueprints(package) helper
  openapi/
    spec_builder.py       hand-curated public login-only OpenAPI document
    routes.py             /openapi/v1-public.json (public) + /openapi/v1.json (protected, generated)
  tests/                 25 tests: app factory, health, platform blueprint, OpenAPI split, discovery
  requirements.in/.txt   hash-pinned direct deps (flask_core installed separately, see Dockerfile)
  Dockerfile             multi-stage, rootless, hypercorn CMD
```

### Porting a controller group (the extension point)

Add exactly ONE file: `blueprints/v1/<group>.py` or `blueprints/v2/<group>.py`,
exposing a module-level `BLUEPRINTS: list[Blueprint]` (each blueprint's
`url_prefix` already the full `/api/v{1,2}/...` path). `routers/v1.py` and
`routers/v2.py` auto-discover every module in their respective
`blueprints/v{1,2}/` package (`routers/_discovery.py`, sorted by module
name for deterministic registration order) and mount whatever
`BLUEPRINTS` it exposes -- a module without one is skipped with a log
line, not an error.

**Never edit `routers/v1.py`, `routers/v2.py`, or `blueprints/__init__.py`
to add a group** -- those three files are shared infrastructure, not a
per-port touch point. This is what makes ~10 parallel port agents safe:
every agent's PR adds a new file under `blueprints/v{1,2}/`, so there is
no shared file to collide on.

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

All 25 tests use `sqlite:memory` (pydal) -- no external Postgres dependency.

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
  bundle-oriented. `blueprints/v2/platform.py` is mounted at
  `/api/v2/core/platform/default/*` as the one worked example.

## Known gaps (tracked, not fixed here)

- `libs/flask_core` ships no `py.typed` marker and `tenant_middleware`/
  `require_scope`'s inner wrappers are unannotated -- every consumer sees
  mypy `--strict`'s `untyped-decorator`; worked around here with scoped,
  documented `# type: ignore[untyped-decorator]` (see `blueprints/v2/platform.py`,
  `openapi/routes.py`).
- `AsyncDAL.close_async()` (`libs/flask_core/flask_core/database.py`)
  closes the underlying pydal `DAL` from a different thread than created
  it, which pydal's thread-local bookkeeping rejects. `app.py`'s shutdown
  hook catches and logs this rather than crashing the ASGI lifespan
  (matching `services/core-community/app.py`'s existing pattern).
- gRPC (backend.md's mandatory service-to-service transport) is not wired
  in this scaffold -- REST + MCP only. Follow-up, not blocking M1.
- `quart-schema==0.25.0` + `pydantic==2.13.x`: `POST .../shoutout/creators`
  (`blueprints/v1/bot.py::add_shoutout_creator`, M5) reproducibly hits
  `TypeError: 'None' is not an instance of 'SchemaSerializer'` in
  `quart_schema`'s app-level second response-dump pass, specific to this
  one route once registered on the real `bot_bp` (bisected -- an
  equivalent hand-built route with identical DTOs does not reproduce it;
  root cause not identified). Worked around by skipping
  `@validate_response` on that single handler and building the response
  dict via `dataclasses.asdict` instead -- the DTO (`ShoutoutCreatorResponse`)
  stays the documented, OpenAPI-generated contract; only the runtime
  double-validation is skipped. See the handler's own docstring.
