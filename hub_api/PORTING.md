# Porting a Node controller group into hub-api

The recipe M1 (Core Identity/Auth: auth, identity, passkey, userManagement,
profile) established for M2..M9. Read this before you start; it will save
you from re-discovering the gotchas in the "Hard-Won Gotchas" section the
slow way.

## The checklist (per controller group)

```
[ ] 1. Read the Node source: controllers/<X>Controller.js + its routes/<x>.js
       mount point + any services/*.js it calls. Grep
       admin/hub_module/frontend/src/services/api.js for every path your
       group owns -- that file is the pinned contract, byte-for-byte.
[ ] 2. Bind your group's pydal tables in services/schema.py's
       bind_<group>_tables(dal, *, migrate=False), called from
       app.py::_bind_reference_tables(). Add `migrate` bool default False
       (test fixtures pass migrate=True) -- see Gotcha #2 below.
       If your group needs new `tenants` columns, extend the ONE
       define_table("tenants", ...) call already in app.py -- never
       redefine the table.
[ ] 3. Service layer in services/<group>_service.py: one function per
       Node controller action, real logic (no dicts as data structures --
       @dataclass(slots=True, frozen=True) return types), pydal query
       builder ONLY (see Gotcha #1 -- raw SQL is Postgres-only here).
[ ] 4. Blueprint in blueprints/v1/<group>.py: route -> tenant_middleware
       (skip for pre-auth routes: login, register, oauth start/callback,
       refresh, public lookups) -> require_scope (skip for self-service
       routes on the caller's OWN resource -- see "Auth pattern" below)
       -> @validate_request/@validate_response DTOs (skip @validate_response
       specifically where Gotcha #3 bites -- use jsonify_dto() instead).
       Path + method IDENTICAL to the Node route. camelCase DTO field
       names where the JSON contract needs them (see "DTO casing" below).
[ ] 5. Add `services/<group>_service.py` and `blueprints/v1/<group>.py` to
       pyproject.toml's per-file-ignores ONLY for the specific, justified
       rules your group also needs (N815 for camelCase DTOs, S101 for
       postcondition asserts) -- copy the pattern already there for auth.py.
[ ] 6. Tests in tests/test_v1_<group>_blueprint.py: standalone Quart app
       registering only your blueprint (see "Test pattern" below), real
       JWTs, real pydal queries. At minimum: one auth-bypass (missing
       token -> 401) and, if your group has an admin-gated route, one
       scope-check (valid token, wrong scope -> 403) test, PLUS a written
       fail-first note (temporarily break the check, confirm the test
       goes red, revert, confirm green -- see any M1 test file's
       docstring for the format).
[ ] 7. `ruff check --fix . && ruff format . && mypy --strict services/
       blueprints/v1/<group>.py` -- must be clean before you open a PR.
[ ] 8. Run the FULL test suite (`pytest tests/`), not just your new file --
       confirm you haven't broken app_factory/router_discovery/openapi_docs
       (they assert on `/api/v1/auth/login`'s status code; M1 already
       updated them from 501 to 400 once the stub became real).
```

## Auth pattern (copy exactly)

| Endpoint shape | Decorators |
|---|---|
| Pre-auth (login, register, oauth start/callback, refresh, public tenant lookup) | none of tenant_middleware/require_scope -- there's no JWT yet |
| Self-service (caller acting on their OWN resource: own profile, own identities, own passkeys) | `@tenant_middleware` only -- see `services/current_user.py` for why `require_scope` doesn't apply here |
| Admin/elevated action (superadmin user CRUD, tenant admin actions) | `@tenant_middleware` + `@require_scope("<resource>:<action>")` |

Self-service routes need "who is calling" but `flask_core.tenancy.
TenantContext` only carries the tenant, not the subject. Use
`services.current_user.get_current_user_id(request)` (raises 401) or
`get_optional_current_user_id(request)` (returns `None`) -- both re-decode
the bearer JWT independently, same pattern `flask_core.authz.require_scope`
itself uses (see that module's own docstring for the rationale). Don't
thread a new field through `TenantContext` -- that's shared infra other
groups also build on.

## DTO casing

`app.py`'s `QuartSchema(app, ...)` does not set `convert_casing=True`
(confirmed by reading `quart_schema/extension.py` -- default `False`), so
there is no automatic camelCase↔snake_case conversion. Wire DTOs pinned to
`api.js`'s camelCase JSON (`avatarUrl`, `isSuperAdmin`, ...) need CAMELCASE
PYTHON FIELD NAMES verbatim -- this deliberately breaks normal PEP8
snake_case convention for these specific classes, matching what
`blueprints/v1/auth.py`'s DTOs already do. Add `N815` to your group's
per-file-ignore for this reason, not because the convention doesn't
matter elsewhere.

## Test pattern

Copy `tests/test_v1_auth_blueprint.py`'s shape: a `Quart(__name__)` +
`QuartSchema(app)` app registering ONLY your blueprint (not the full
`create_app()`), `app.config["dal"]`/`["async_dal"]` from the `auth_db`
fixture (`tests/conftest.py`), `app.config["HUB_API_CONFIG"]` from a
locally-built `HubAPIConfig`. `auth_headers`/`user_auth_headers` fixtures
mint real JWTs via `flask_core.auth.create_jwt_token` -- never hand-roll
one. If your group needs tables `bind_auth_tables()` doesn't already
cover, add your own `bind_<group>_tables()` call to `auth_db` (or a new
fixture) in `tests/conftest.py` -- additive only, never edit the M1
group's own fixture logic.

---

## Hard-Won Gotchas

### Gotcha #1 -- `async_dal`'s raw-SQL helpers are Postgres-only; use the pydal query builder

`flask_core.database.AsyncDAL.executesql_async()`/`.execute()` both
hardcode `%s` placeholders (psycopg2's paramstyle). Any raw SQL string
using `%s` will 500 with `sqlite3.OperationalError: near "%": syntax
error` the moment a test runs it against sqlite -- and
`backend-database.md` mandates supporting every `DB_TYPE`, not just
Postgres. **Use pydal's query builder for everything**, including JOINs
(`left=dal.other_table.on(...)`) and `DISTINCT`
(`select_async(dal(query), field, distinct=True)`) -- it's portable and
it's the only form these tests can exercise. `auth_service.py`,
`profile_service.py`, and `user_management_service.py` all had raw-SQL
call sites converted during the M1 port; read `list_users()` in
`user_management_service.py` for a WHERE-clause-with-optional-filters
example, or `get_my_profile()` in `profile_service.py` for a LEFT JOIN
example.

Second half of this gotcha: `select_async(query, ...)` expects `query` to
already be a pydal **`Set`** (i.e. `dal(condition)`), NOT a bare `Query`
(`dal.table.field == value`) -- passing a bare `Query` fails with
`AttributeError: 'Query' object has no attribute 'select'`.
`update_async`/`delete_async`/`count_async` self-wrap (`self.dal(query)`
internally) so a bare `Query` is correct there -- only `select_async` is
the odd one out. (`flask_core.auth.verify_api_key_async`'s own example
usage has this exact bug -- don't copy it.)

### Gotcha #2 -- `sqlite:memory` breaks the moment a route calls `async_dal.*_async()`

`AsyncDAL`'s DB calls run on its own `ThreadPoolExecutor` (a different OS
thread per call). SQLite's `:memory:` database is connection-scoped --
each new connection (i.e. each new executor thread) sees a BLANK
database, not the one the main thread just seeded. Symptom:
`sqlite3.OperationalError: no such table: hub_users` even though you just
defined and inserted into it. `tests/conftest.py::tenant_db` (the
pre-M1 fixture) never hits this because `tenant_middleware` queries
`dal(query).select()` synchronously on the request thread, no executor
involved -- but the moment YOUR service layer calls `select_async`/
`insert_async`, you need a file-backed sqlite DB instead:
`AsyncDAL(f"sqlite://{tmp_path}/test.db", pool_size=1)` -- see
`tests/conftest.py::auth_db`. `pool_size=1` avoids a SECOND sqlite
footgun (`database is locked` from concurrent connections against a
non-WAL file).

Related: `bind_<group>_tables()` must accept `migrate: bool = False` and
thread it into every `dal.define_table(..., migrate=migrate)` call.
Production never migrates (schema owned by `config/postgres/migrations/`);
tests need `migrate=True` or pydal never issues the `CREATE TABLE` DDL at
all against the throwaway sqlite file, and every query 500s with
"no such table" regardless of the connection-scoping fix above.

### Gotcha #3 -- a specific `@validate_response` + real DB write + nested-dataclass response crashes

Confirmed, 100%-reproducible, isolated across 17 throwaway repro scripts
(not kept in this repo) against this repo's exact pinned versions
(pydantic 2.13.5 / pydantic-core 2.46.5 / quart-schema 0.25.0): a route
that awaits a real `async_dal.insert_async()` (or, in one case,
`update_async()`) and then returns a dataclass with a NESTED dataclass
field (e.g. `user: LoginUserDTO`) raises `TypeError: 'None' is not an
instance of 'SchemaSerializer'` from inside pydantic-core -- whether or
not `@validate_response` decorates the route, since quart-schema's
app-wide `make_response` hook runs `TypeAdapter(type(raw)).dump_python()`
on every response regardless of decoration.

Root cause NOT fully identified (time-boxed after exhausting: Optional
fields, GC timing, thread-pool warm-up order, bcrypt cost factor, import-
lock contention, dict-vs-dataclass, specific-table -- none of these were
it). It reproduces with `login()`-shaped flows in a minimal harness but
NOT through the real `/api/v1/auth/login` route, and does NOT reproduce
for flows that only `select`/`update` (never `insert`) before a nested
response. If you hit this (a route 500s with exactly this `TypeError` and
your DTO shapes look correct), don't spend a day on it like this PR did --
apply the workaround directly:

```python
from services.dto_response import jsonify_dto

@my_bp.route("/thing", methods=["POST"])
@validate_request(MyRequest)
# NOT @validate_response -- see services/dto_response.py's module docstring.
async def create_thing(data: MyRequest) -> tuple[Any, int]:
    ...
    return jsonify_dto(MyNestedResponse(success=True, thing=ThingDTO(...)))
```

`jsonify_dto()` builds a real `quart.Response` via `jsonify()`, which
`model_dump`'s internal branching leaves untouched (falls through to
`else: value = raw`) -- the crash never triggers. This is NOT a "raw
dict"/`**model.__dict__` violation of security.md's Output Validation
rule: the DTO's `dataclass(slots=True)` constructor already fixed the
exact field set before `dataclasses.asdict()` ever runs.

Routes fixed this way in M1: `register()`, `verify_email()` (auth.py);
`create_user()`, `update_user()`, `assign_analytics_consumer_role()`
(user_management.py); `update_my_profile()` (profile.py). Flat responses
(no nested dataclass field) and select-only routes were empirically
confirmed safe with normal `@validate_response` throughout M1's own test
suite -- don't apply `jsonify_dto()` everywhere defensively, only where a
failing test proves you need it.

### Gotcha #4 -- schema gaps between Node's code and the real migrations

Three columns Node's controllers reference don't exist in
`config/postgres/migrations/*.sql` (only in a separately-drifted
`config/postgres/init.sql` or nowhere at all): `hub_users.
email_verification_expires`, `hub_oauth_states.metadata`,
`platform_configs.enabled`. These are pre-existing gaps, not introduced
by the Python port -- Node's own code would 500 against the real
migrated schema too. `services/schema.py`'s module docstring documents
all three and the specific workaround chosen for each (bind the column
anyway to stay byte-faithful; for `hub_oauth_states.metadata`, drop the
tenant-scoped OAuth-state stashing and resolve against
`DEFAULT_TENANT_SLUG` instead of porting a call that would 500). If your
group hits a similar gap, follow the same pattern: document it, don't
silently invent a column, don't silently drop the whole feature either.

### Gotcha #5 -- `dal.tables` empty-route trick

`@blueprint.route("", methods=["GET"])` (empty string, not `"/"`) with a
non-empty `url_prefix` produces the prefix path EXACTLY, no trailing
slash -- e.g. `url_prefix="/api/v1/user/identities"` + `route("")` ->
`/api/v1/user/identities`. `route("/")` instead would register
`.../identities/` (trailing slash), a different path than Node's
contract. Confirmed via direct `app.url_map` inspection during the M1
port.

---

## What M1 does NOT cover (explicit scope boundaries, not gaps)

- OAuth is scoped to Discord/Twitch/Slack (`flask_core.auth.
  OAUTH_PROVIDERS`'s own coverage) -- Node's `youtube`/`kick` support is
  not ported. Add them to `oauth_service.py`'s `VALID_PLATFORMS` +
  provider-URL tables if/when a group needs them.
- `profileController.js`'s `getPublicProfile`/`getMemberProfile` (mounted
  under `public.js`/`community.js` in Node, not `user.js`) belong to the
  Public/Tenancy groups, not M1 -- only the self-service subset
  (`getMyProfile` and friends) is ported here.
- `authController.js`'s `linkOAuth()` (legacy temp-password OAuth
  linking) is dead code under the current unified-session model (writes
  a field, `req.user.platformUserId`, that `createSession()` never sets)
  -- ported as an honest `501`, not a faithful reproduction of a
  guaranteed-broken code path. Confirm with product whether this route
  can be retired from the v1 contract entirely.
- Email delivery (Node's `sendVerificationEmail()`) is not wired --
  hub-api has no SMTP/email client dependency yet. Verification tokens
  are generated and stored regardless, so `verify_email()` is fully
  functional once a caller has the token; only the "send it" transport
  leg is missing.
- `userManagementController.js`'s `getUserDeletionRequest()` queries
  `data_deletion_requests`, a table owned by the Privacy/Compliance group
  (M3) and not bound in `services/schema.py` -- still uses a raw-SQL
  `%s` query (Gotcha #1 applies) and is untested against sqlite. Convert
  it and bind the table when M3 lands, or sooner if you need it tested.
