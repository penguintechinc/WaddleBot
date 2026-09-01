"""Public, unauthenticated OpenAPI document -- zero paths, by design.

backend.md OpenAPI: "Docs/spec endpoints MUST be authenticated, one
exception: the login endpoint... Implement as two documents (minimal
public login-only spec + full spec behind the same JWT/OIDC middleware as
the rest of the API)." svc-streaming has NO login endpoint of its own --
every route requires a bearer JWT minted by hub-api's auth service
(`security.md` JWT + OIDC mandatory) -- so its public document has zero
paths rather than a borrowed login contract that doesn't actually exist
here. This still satisfies the rule's intent: an unauthenticated caller
learns nothing about this service's real surface from this endpoint.
"""

from __future__ import annotations

from typing import Any


def build_public_spec(*, title: str, version: str) -> dict[str, Any]:
    """Return the minimal public OpenAPI 3.x document -- no paths, this service has no login."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": f"{title} (public)",
            "version": version,
            "description": (
                "svc-streaming has no public endpoints of its own -- authenticate via "
                "hub-api's login endpoint, then call this service with the issued bearer JWT."
            ),
        },
        "paths": {},
    }
