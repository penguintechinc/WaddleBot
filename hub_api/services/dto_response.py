"""Manual DTO-to-`Response` serialization -- workaround for a quart-schema/pydantic-core crash.

**The bug** (pydantic 2.13.5 / pydantic-core 2.46.5 / quart-schema 0.25.0,
this repo's pinned versions as of the M1 port): a route that (a) awaits a
real `AsyncDAL.insert_async()` call (any table) and then (b) returns a
dataclass instance with a NESTED dataclass field (e.g. `RegisterSuccessResponse.
user: LoginUserDTO`) -- whether or not `@validate_response` is present, since
quart-schema's app-wide `make_response` hook (`convert_response_return_value`
-> `model_dump` -> `TypeAdapter(type(raw)).dump_python(raw)`) runs on EVERY
response regardless of decoration -- reliably raises `TypeError: 'None' is
not an instance of 'SchemaSerializer'` from inside pydantic-core's Rust
extension.

**Isolated the hard way** (17 throwaway repro scripts, not kept in this
repo): NOT about Optional fields, NOT about which specific classes are
involved, NOT about `sqlite` vs the executor thread pool alone (a bare
`insert_async()` followed by a bare `dict` return -- no custom classes at
all -- reproduces it too), NOT bcrypt, NOT a specific table, NOT GC timing,
NOT import-lock contention. It IS specifically: `insert_async()` (or more)
awaited, THEN a nested-dataclass response serialized through quart-schema's
`TypeAdapter` path, in THIS exact dependency version combination. `login()`
(no insert into `hub_users`, only `hub_sessions`) does not trip it under
every code path tried; `register()`/`verify_email()` (insert into
`hub_users`) do, 100% reproducibly. Root cause not fully identified --
time-boxed; flagged as a dependency-version issue to revisit (see
`hub_api/PORTING.md`), not chased further within this port PR.

**The workaround**: a `quart.Response` object (built via `quart.jsonify`)
falls through `model_dump`'s final `else: value = raw` branch UNCHANGED --
`TypeAdapter` never runs, the crash never triggers. `jsonify_dto()` below
is the one place every group hitting this same crash should route through:
construct the real (slotted, frozen) DTO via its constructor as always --
that already guarantees the exact field set, `@validate_response`'s own
enforcement mechanism, no less -- then convert with `dataclasses.asdict()`
and hand it to `jsonify()` instead of returning the dataclass directly. NOT
a raw dict/`**model.__dict__` in the security.md Output Validation sense:
the DTO's `__slots__` already fixed the field set at construction time.

Use ONLY on routes that hit this crash (confirmed via a failing test) --
`@validate_response` is strictly better everywhere else (OpenAPI schema
generation, automatic 500 on a shape mismatch) and remains the default
pattern every other route in this port follows.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from quart import Response, jsonify


def jsonify_dto(dto: Any, status: int = 200) -> tuple[Response, int]:
    """Convert a slotted dataclass DTO instance to a `(Response, status)` tuple.

    Bypasses quart-schema's `TypeAdapter`-based response conversion --
    see this module's docstring for why that's currently necessary for
    a small set of routes.
    """
    return jsonify(dataclasses.asdict(dto)), status
