"""
Customer Module -- MVP Quart skeleton
========================================

Customer is 100% green-field (no pre-v3 code to convert, per the design
doc's ``Modules`` table), so this is the registration point for
:mod:`customer_module.features` plus one worked gate example --
``POST /customer/accounts`` -- wired end-to-end against
``waddles.customer.accounts``, not the full CRM (a multi-year effort per
the design doc). The other four Features (contacts, opportunities,
pipelines, cases) follow this identical one-line guard once their own
handlers exist.
"""

from __future__ import annotations

import asyncio
from typing import Any, Tuple

from flask_core.api_utils import async_endpoint, error_response, success_response
from flask_core.feature_flags import feature_enabled
from flask_core.tenancy import DEFAULT_TENANT_SLUG, get_tenant_context, tenant_middleware
from quart import Blueprint, Quart, request

app = Quart(__name__)
api_bp = Blueprint("customer_api", __name__, url_prefix="/customer")


@api_bp.route("/accounts", methods=["POST"])
# regression: tenant-isolation audit 2026-08-30 -- tenant_middleware was
# missing here, so get_tenant_context(request) always returned None and
# every request silently ran as DEFAULT_TENANT_SLUG with no auth. Must be
# the outermost decorator (security.md: tenant before scope/handler logic)
# so an invalid/missing JWT 401s before async_endpoint's error handling or
# the handler body ever run.
@tenant_middleware
@async_endpoint
async def create_account() -> Tuple[Any, int]:
    """
    Create a Customer account -- the worked Feature gate for this module.

    Guards on ``waddles.customer.accounts`` (customer.accounts, free tier)
    before doing anything else; a disabled flag no-ops with 404 rather than
    executing stub logic. This is an MVP stub (returns a placeholder
    record), not the full account-creation flow.
    """
    tenant_ctx = get_tenant_context(request)
    tenant_slug = tenant_ctx.tenant_slug if tenant_ctx is not None else DEFAULT_TENANT_SLUG
    data = await request.get_json(silent=True) or {}
    community_id = data.get("community_id")

    if not await feature_enabled(
        "waddles.customer.accounts", tenant=tenant_slug, community=community_id
    ):
        return error_response("customer.accounts is not available", status_code=404)

    return success_response({"id": "stub-account", "name": data.get("name")})


app.register_blueprint(api_bp)

if __name__ == "__main__":
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    config = HyperConfig()
    config.bind = ["0.0.0.0:8080"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
