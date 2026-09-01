"""OpenAPI document routes -- the public (empty) one, and the full one, both auth-consistent.

Two routes, two trust levels (backend.md OpenAPI), mirroring `hub_api/
openapi/routes.py`'s exact split:

- `GET /openapi/v1-public.json` -- unauthenticated, zero paths
  (`spec_builder.build_public_spec`).
- `GET /openapi/v1.json` -- the complete, generated document (every
  mounted route, `quart_schema`'s own introspection), behind
  `tenant_middleware` + `require_scope("streaming:read")` -- the SAME auth
  chain as any other protected route on this service, not a bespoke
  check. This is what the default (disabled -- see `app.py`'s
  `QuartSchema(..., openapi_path=None, swagger_ui_path=None)`)
  `/openapi.json`/`/docs` routes would have served unauthenticated;
  mounting it behind auth instead is the entire fix.
"""

from __future__ import annotations

from typing import Any, cast

from flask_core.authz import require_scope
from flask_core.tenancy import tenant_middleware
from quart import Blueprint, current_app

from .spec_builder import build_public_spec

openapi_bp = Blueprint("openapi_docs", __name__, url_prefix="/openapi")


@openapi_bp.route("/v1-public.json", methods=["GET"])
async def public_spec() -> dict[str, Any]:
    """The minimal, unauthenticated, zero-path OpenAPI document."""
    cfg = current_app.config["APP_CONFIG"]
    return build_public_spec(title=cfg.module_name, version=cfg.module_version)


@openapi_bp.route("/v1.json", methods=["GET"])
# flask_core ships no py.typed marker -- same known upstream mypy-strict
# gap `hub_api/openapi/routes.py` documents; ignored at this one call
# site rather than silencing --strict project-wide.
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("streaming:read")  # type: ignore[untyped-decorator]
async def full_spec() -> dict[str, Any]:
    """The complete, auto-generated OpenAPI document -- every mounted route."""
    provider = current_app.extensions["QUART_SCHEMA"].openapi_provider
    return cast(dict[str, Any], provider.schema())


def register_openapi_docs(app: Any) -> None:
    """Mount both OpenAPI document routes onto `app`."""
    app.register_blueprint(openapi_bp)
