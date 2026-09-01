"""Manual DTO-to-`Response` serialization -- ported from `hub_api/services/dto_response.py`.

Same pinned quart-schema/pydantic-core crash hub-api's M1 port hit and
documented at length (`hub_api/PORTING.md` Gotcha #3, this module's
upstream twin's own docstring): a route that awaits a real
`AsyncDAL.insert_async()`/`update_async()` call and then returns a
dataclass with a NESTED dataclass field raises `TypeError: 'None' is not
an instance of 'SchemaSerializer'` from inside pydantic-core, regardless
of whether `@validate_response` decorates the route. This service pins
the identical `quart`/`quart-schema` versions (`requirements.in`), so the
same routes are exposed to the same crash -- `blueprints/streaming.py`'s
write routes (`set_config`, `add_target`, `start_forwarding`,
`stop_forwarding`) all await an insert/update immediately before
returning a nested-dataclass response and route through `jsonify_dto()`
instead of `@validate_response` for exactly that reason.

Use ONLY where a real insert/update precedes a nested-dataclass response
-- select-only routes (`get_config`, `list_targets`, `get_status`) are
empirically safe with `@validate_response` and keep using it.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from quart import Response, jsonify


def jsonify_dto(dto: Any, status: int = 200) -> tuple[Response, int]:
    """Convert a slotted dataclass DTO instance to a `(Response, status)` tuple.

    NOT a raw dict/`**model.__dict__` violation of security.md's Output
    Validation rule: the DTO's `dataclass(slots=True)` constructor already
    fixed the exact field set before `dataclasses.asdict()` runs.
    """
    return jsonify(dataclasses.asdict(dto)), status
