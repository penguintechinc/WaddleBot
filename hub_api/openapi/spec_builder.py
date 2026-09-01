"""Public, unauthenticated OpenAPI document -- the login endpoint, and nothing else.

backend.md OpenAPI: "Docs/spec endpoints MUST be authenticated, one
exception: the login endpoint... Implement as two documents (minimal
public login-only spec + full spec behind the same JWT/OIDC middleware
as the rest of the API), not one gated-or-not toggle." This module is
that first document.

Deliberately hand-curated rather than generated: quart-schema's own
introspection (`quart_schema.openapi.OpenAPIProvider.generate_rules`)
walks every registered, non-hidden route on the app, which is exactly
the unauthenticated-full-surface-exposure this rule exists to prevent.
A hand-authored, single-path document only ever grows when someone edits
this file -- never when someone adds an unrelated route elsewhere in
hub-api and forgets it's public by default.

The one path here (`POST /api/v1/auth/login`) documents the frozen
contract shape from `admin/hub_module/frontend/src/services/api.js`, the
pinned source of truth per the migration plan -- not the scaffold stub's
current 501 behavior (`routers/v1.py`), which lands for real in M1.
"""

from __future__ import annotations

from typing import Any


def build_public_login_spec(*, title: str, version: str) -> dict[str, Any]:
    """Return the minimal public OpenAPI 3.x document -- exactly one path."""
    return {
        "openapi": "3.1.0",
        "info": {"title": f"{title} (public)", "version": version},
        "paths": {
            "/api/v1/auth/login": {
                "post": {
                    "summary": "Authenticate and obtain a JWT (public, unauthenticated)",
                    "operationId": "login",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["username", "password"],
                                    "properties": {
                                        "username": {"type": "string"},
                                        "password": {"type": "string", "format": "password"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "JWT issued",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "token": {"type": "string"},
                                            "expires_in": {"type": "integer"},
                                        },
                                    }
                                }
                            },
                        },
                        "401": {"description": "Invalid credentials"},
                    },
                }
            }
        },
    }
