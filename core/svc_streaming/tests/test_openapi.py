"""OpenAPI document route tests -- public (zero paths) vs full (authenticated + scoped)."""

from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import TENANT_SLUG, auth_header, make_user_token, seed_tenant


@pytest.mark.asyncio
async def test_public_spec_is_unauthenticated_and_has_zero_paths(app_and_client: Any) -> None:
    _, client = app_and_client
    response = await client.get("/openapi/v1-public.json")
    assert response.status_code == 200
    body = await response.get_json()
    assert body["paths"] == {}


@pytest.mark.asyncio
async def test_full_spec_requires_auth(app_and_client: Any) -> None:
    _, client = app_and_client
    response = await client.get("/openapi/v1.json")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_full_spec_requires_streaming_read_scope(app_and_client: Any, dal_pair: Any) -> None:
    _, client = app_and_client
    _, dal = dal_pair
    seed_tenant(dal, slug=TENANT_SLUG)
    token = make_user_token(user_id=1, scope="")  # authenticated, but no scope granted

    response = await client.get("/openapi/v1.json", headers=auth_header(token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_full_spec_returns_generated_document_with_correct_scope(
    app_and_client: Any, dal_pair: Any
) -> None:
    _, client = app_and_client
    _, dal = dal_pair
    seed_tenant(dal, slug=TENANT_SLUG)
    token = make_user_token(user_id=1, scope="streaming:read")

    response = await client.get("/openapi/v1.json", headers=auth_header(token))
    assert response.status_code == 200
    body = await response.get_json()
    assert "paths" in body
    assert len(body["paths"]) > 0  # real, quart-schema-generated -- every mounted route
