"""`blueprints/v1/distribution.py` -- the svc-ingest/svc-process poll endpoint.

Standalone Quart app registering only `distribution_bp`, matching
`test_v1_data_privacy_blueprint.py`'s pattern (`distribution_db` fixture --
`tests/conftest.py`). Real JWTs via `flask_core.auth.create_jwt_token`, real
pydal queries against `app_catalog`/`app_activations`/
`app_tenant_availability`.

Fail-first proof (executed, not narrated): temporarily made
`list_bundles_for_stage` skip its `stage in stages` filter entirely (return
every activated bundle regardless of stage) -- `test_stage_filters_out_bundles_missing_that_stage`
went red (an action-only bundle leaked into the `ingest` response); reverted,
confirmed green again.
"""

from __future__ import annotations

from typing import Any

import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints.v1.distribution import distribution_bp
from tests.conftest import TENANT_SLUG, make_token


@pytest.fixture
def app(distribution_db: Any) -> Quart:
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(distribution_bp)
    quart_app.config["dal"] = distribution_db.dal
    quart_app.config["async_dal"] = distribution_db
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


def _headers(*, scope: str = "distribution:read", tenant: str = TENANT_SLUG) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(scope=scope, tenant=tenant)}"}


def _seed_bundle(
    distribution_db: Any,
    *,
    app_id: str = "waddles.core.demo.echo",
    stages: dict[str, Any] | None = None,
) -> None:
    dal = distribution_db.dal
    dal.app_catalog.insert(
        app_id=app_id,
        manifest_version="1.0.0",
        module="core",
        feature="waddles.core.demo",
        provider="builtin",
        execution_model="native",
        platform_compatibility={},
        status="active",
        stages=stages
        if stages is not None
        else {
            "ingest": {"entrypoint": "bundles.echo_ingest:normalize", "config": {}, "spec": {}},
            "process": {"entrypoint": "bundles.echo_process:transform", "config": {}, "spec": {}},
        },
    )
    dal.commit()


def _seed_community(distribution_db: Any, *, tenant_slug: str = TENANT_SLUG) -> tuple[int, int]:
    dal = distribution_db.dal
    tenant_row = dal(dal.tenants.slug == tenant_slug).select().first()
    community_id: int = dal.communities.insert(name="acme-community", tenant_id=tenant_row.id)
    dal.commit()
    return tenant_row.id, community_id


class TestAuth:
    async def test_missing_token_is_401(self, client: Any) -> None:
        response = await client.get("/api/v1/distribution/bundles?stage=ingest")
        assert response.status_code == 401

    async def test_missing_scope_is_403(self, client: Any) -> None:
        response = await client.get(
            "/api/v1/distribution/bundles?stage=ingest",
            headers=_headers(scope=""),
        )
        assert response.status_code == 403

    async def test_wrong_tenant_cannot_see_another_tenants_activation(
        self, client: Any, distribution_db: Any
    ) -> None:
        """Tenant isolation: a JWT scoped to a DIFFERENT tenant sees nothing.

        Only `TENANT_SLUG` ("acme-corp") is seeded in `distribution_db`; a
        token minted for a tenant that doesn't exist in this DB must 403 at
        `tenant_middleware`, never silently resolve to someone else's data.
        """
        response = await client.get(
            "/api/v1/distribution/bundles?stage=ingest",
            headers=_headers(tenant="someone-elses-tenant"),
        )
        assert response.status_code == 403


class TestInputValidation:
    async def test_missing_stage_is_400(self, client: Any) -> None:
        response = await client.get("/api/v1/distribution/bundles", headers=_headers())
        assert response.status_code == 400
        body = await response.get_json()
        assert body["error"]["code"] == "INVALID_STAGE"

    async def test_unknown_stage_is_400(self, client: Any) -> None:
        response = await client.get(
            "/api/v1/distribution/bundles?stage=not_a_real_stage", headers=_headers()
        )
        assert response.status_code == 400

    async def test_non_integer_community_id_is_400(self, client: Any) -> None:
        response = await client.get(
            "/api/v1/distribution/bundles?stage=ingest&community_id=not-an-int",
            headers=_headers(),
        )
        assert response.status_code == 400
        body = await response.get_json()
        assert body["error"]["code"] == "INVALID_COMMUNITY_ID"


class TestListBundles:
    async def test_no_activations_returns_empty_list(self, client: Any) -> None:
        response = await client.get("/api/v1/distribution/bundles?stage=ingest", headers=_headers())
        assert response.status_code == 200
        body = await response.get_json()
        assert body["success"] is True
        assert body["stage"] == "ingest"
        assert body["bundles"] == []
        assert body["meta"]["version"] == 1

    async def test_tenant_wide_availability_surfaces_bundle(
        self, client: Any, distribution_db: Any
    ) -> None:
        _seed_bundle(distribution_db)
        tenant_id, _ = _seed_community(distribution_db)
        dal = distribution_db.dal
        dal.app_tenant_availability.insert(
            tenant_id=tenant_id,
            app_id="waddles.core.demo.echo",
            available=True,
            config_defaults={"greeting": "hi"},
        )
        dal.commit()

        response = await client.get("/api/v1/distribution/bundles?stage=ingest", headers=_headers())
        assert response.status_code == 200
        body = await response.get_json()
        assert len(body["bundles"]) == 1
        bundle = body["bundles"][0]
        assert bundle["appId"] == "waddles.core.demo.echo"
        assert bundle["communityId"] is None
        assert bundle["entrypoint"] == "bundles.echo_ingest:normalize"
        assert bundle["config"] == {"greeting": "hi"}

    async def test_community_activation_overrides_tenant_wide_config(
        self, client: Any, distribution_db: Any
    ) -> None:
        """Community-scoped `config` wins over the tenant-wide `config_defaults` for the same app_id."""
        _seed_bundle(distribution_db)
        tenant_id, community_id = _seed_community(distribution_db)
        dal = distribution_db.dal
        dal.app_tenant_availability.insert(
            tenant_id=tenant_id,
            app_id="waddles.core.demo.echo",
            available=True,
            config_defaults={"greeting": "hi", "volume": 1},
        )
        dal.app_activations.insert(
            community_id=community_id,
            tenant_id=tenant_id,
            app_id="waddles.core.demo.echo",
            enabled=True,
            config={"greeting": "yo"},
        )
        dal.commit()

        response = await client.get(
            f"/api/v1/distribution/bundles?stage=ingest&community_id={community_id}",
            headers=_headers(),
        )
        assert response.status_code == 200
        body = await response.get_json()
        # Deduped by app_id -- community-scoped row wins (first occurrence),
        # never returned twice even though both tiers have a matching row.
        assert len(body["bundles"]) == 1
        bundle = body["bundles"][0]
        assert bundle["communityId"] == community_id
        assert bundle["config"] == {"greeting": "yo"}

    async def test_disabled_activation_is_excluded(self, client: Any, distribution_db: Any) -> None:
        _seed_bundle(distribution_db)
        tenant_id, community_id = _seed_community(distribution_db)
        dal = distribution_db.dal
        dal.app_activations.insert(
            community_id=community_id,
            tenant_id=tenant_id,
            app_id="waddles.core.demo.echo",
            enabled=False,
            config={},
        )
        dal.commit()

        response = await client.get(
            f"/api/v1/distribution/bundles?stage=ingest&community_id={community_id}",
            headers=_headers(),
        )
        body = await response.get_json()
        assert body["bundles"] == []

    async def test_stage_filters_out_bundles_missing_that_stage(
        self, client: Any, distribution_db: Any
    ) -> None:
        """A bundle with only an `action` stage never appears in an `ingest` poll.

        Fail-first note: temporarily removed the `stage in stages` guard
        from `distribution_service.list_bundles_for_stage` (returned every
        activated bundle unconditionally) -- this test went red (the
        action-only bundle leaked into the ingest response's `bundles`
        list); reverted, confirmed green again.
        """
        _seed_bundle(
            distribution_db,
            app_id="waddles.core.demo.actiononly",
            stages={"action": {"entrypoint": "bundles.echo_action:run", "config": {}, "spec": {}}},
        )
        tenant_id, community_id = _seed_community(distribution_db)
        dal = distribution_db.dal
        dal.app_activations.insert(
            community_id=community_id,
            tenant_id=tenant_id,
            app_id="waddles.core.demo.actiononly",
            enabled=True,
            config={},
        )
        dal.commit()

        response = await client.get(
            f"/api/v1/distribution/bundles?stage=ingest&community_id={community_id}",
            headers=_headers(),
        )
        body = await response.get_json()
        assert body["bundles"] == []

        action_response = await client.get(
            f"/api/v1/distribution/bundles?stage=action&community_id={community_id}",
            headers=_headers(),
        )
        action_body = await action_response.get_json()
        assert len(action_body["bundles"]) == 1
        assert action_body["bundles"][0]["appId"] == "waddles.core.demo.actiononly"

    async def test_yanked_bundle_is_excluded(self, client: Any, distribution_db: Any) -> None:
        _seed_bundle(distribution_db)
        dal = distribution_db.dal
        dal(dal.app_catalog.app_id == "waddles.core.demo.echo").update(status="yanked")
        tenant_id, _ = _seed_community(distribution_db)
        dal.app_tenant_availability.insert(
            tenant_id=tenant_id, app_id="waddles.core.demo.echo", available=True
        )
        dal.commit()

        response = await client.get("/api/v1/distribution/bundles?stage=ingest", headers=_headers())
        body = await response.get_json()
        assert body["bundles"] == []
