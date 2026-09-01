"""`blueprints/v1/marketplace_lifecycle.py` -- App Bundle 3-tier lifecycle group.

Standalone Quart app registering only `marketplace_lifecycle_bp`, matching
`test_v1_tenant_blueprint.py`'s pattern.

Fail-first proofs (executed, not narrated):

1. Superset invariant #1 (`available <= installed`) -- temporarily replaced
   `services/marketplace_lifecycle_service.py::make_available`'s
   `check_availability_insert_allowed` call with a bare `pass`:
   `test_make_available_without_install_is_409` went red (201 instead of
   409, a tenant could make ANY app_id "available" with no corresponding
   `app_catalog` row); reverted, green again.
2. Superset invariant #2 (`activated <= available`) -- temporarily replaced
   `activate_bundle`'s `check_activation_insert_allowed` call with a bare
   `pass`: `test_activate_without_availability_is_409` went red (201
   instead of 409); reverted, green again.
3. Per-community IDOR (`authorize_community`'s tenant-ownership re-check) --
   temporarily hardcoded `admin=False` bypass by commenting out the
   `resolve_community_membership_scoped` community-tenant-ownership guard
   clause (`if not community_rows: return None`) in
   `services/community_authz.py`: `test_activate_cross_tenant_community_is_403`
   went red (201 instead of 403 -- a community-admin of the FIRST tenant's
   community could activate a bundle against the SECOND tenant's
   `community_id`); reverted, green again.
"""

from __future__ import annotations

from typing import Any

import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints.v1.marketplace_lifecycle import marketplace_lifecycle_bp
from flask_core.app_registry import get_registry
from tests.conftest import (
    LIFECYCLE_COMMUNITY_ID,
    LIFECYCLE_OTHER_COMMUNITY_ID,
    OTHER_TENANT_SLUG,
    TENANT_SLUG,
    make_user_token,
)

APP_ID_A = "waddles.bot.shoutout.custom-a"
APP_ID_B = "waddles.bot.shoutout.custom-b"


def _manifest(app_id: str, *, incompatible_with: list[str] | None = None) -> dict[str, Any]:
    return {
        "appId": app_id,
        "name": "Custom Shoutout",
        "version": "1.0.0",
        "feature": "waddles.bot.shoutout",
        "module": "bot",
        "provider": "builtin",
        "executionModel": "native",
        "isDefault": False,
        "compatibleWith": [],
        "incompatibleWith": incompatible_with or [],
        "platformCompatibility": {"testedWith": "release/v3.0.X"},
    }


@pytest.fixture(autouse=True)
def _clear_registry() -> Any:
    """`AppRegistry` is a process-wide singleton -- clear it before/after every test.

    Without this, `install_bundle()`'s `reg.register(manifest)` raises
    `RegistryError` (`duplicate_app_id`) the second time any test in this
    module installs `APP_ID_A`/`APP_ID_B`, since the registry survives
    across tests within the same pytest process (unlike the per-test
    sqlite fixture).
    """
    get_registry().clear()
    yield
    get_registry().clear()


@pytest.fixture
def app(lifecycle_db: Any) -> Quart:
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(marketplace_lifecycle_bp)
    quart_app.config["dal"] = lifecycle_db.dal
    quart_app.config["async_dal"] = lifecycle_db
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


def _platform_admin_headers() -> dict[str, str]:
    token = make_user_token(user_id=1, scope="platform:admin", tenant=TENANT_SLUG)
    return {"Authorization": f"Bearer {token}"}


def _tenant_admin_headers(*, tenant: str = TENANT_SLUG) -> dict[str, str]:
    token = make_user_token(user_id=1, scope="tenant:admin", tenant=tenant)
    return {"Authorization": f"Bearer {token}"}


def _community_admin_headers(*, tenant: str = TENANT_SLUG) -> dict[str, str]:
    """User `"1"` -- `lifecycle_db` seeds this exact id as a `community_roles` admin."""
    token = make_user_token(user_id=1, scope="", tenant=tenant)
    return {"Authorization": f"Bearer {token}"}


async def _install(client: Any, app_id: str = APP_ID_A, **kw: Any) -> Any:
    return await client.post(
        "/api/v1/marketplace/bundles",
        headers=_platform_admin_headers(),
        json=_manifest(app_id, **kw),
    )


async def _make_available(client: Any, app_id: str = APP_ID_A) -> Any:
    return await client.post(
        f"/api/v1/marketplace/tenant/{TENANT_SLUG}/bundles",
        headers=_tenant_admin_headers(),
        json={"appId": app_id},
    )


async def _activate(client: Any, app_id: str = APP_ID_A, community_id: int = LIFECYCLE_COMMUNITY_ID) -> Any:
    return await client.post(
        f"/api/v1/marketplace/community/{community_id}/bundles",
        headers=_community_admin_headers(),
        json={"appId": app_id},
    )


class TestInstallUninstall:
    async def test_install_no_token_is_401(self, client: Any) -> None:
        response = await client.post("/api/v1/marketplace/bundles", json=_manifest(APP_ID_A))
        assert response.status_code == 401

    async def test_install_wrong_scope_is_403(self, client: Any) -> None:
        response = await client.post(
            "/api/v1/marketplace/bundles",
            headers=_tenant_admin_headers(),
            json=_manifest(APP_ID_A),
        )
        assert response.status_code == 403

    async def test_install_success_is_201_and_listed(self, client: Any) -> None:
        response = await _install(client)
        assert response.status_code == 201

        listing = await client.get("/api/v1/marketplace/bundles", headers=_tenant_admin_headers())
        assert listing.status_code == 200
        body = await listing.get_json()
        assert body["bundles"][0]["appId"] == APP_ID_A
        assert body["bundles"][0]["status"] == "active"

    async def test_install_duplicate_is_409(self, client: Any) -> None:
        first = await _install(client)
        assert first.status_code == 201
        second = await _install(client)
        assert second.status_code == 409

    async def test_install_bad_manifest_is_400(self, client: Any) -> None:
        bad = _manifest(APP_ID_A)
        bad["appId"] = "not-namespaced"
        response = await client.post(
            "/api/v1/marketplace/bundles", headers=_platform_admin_headers(), json=bad
        )
        assert response.status_code == 400

    async def test_uninstall_sets_status_yanked(self, client: Any) -> None:
        await _install(client)
        response = await client.delete(
            f"/api/v1/marketplace/bundles/{APP_ID_A}", headers=_platform_admin_headers()
        )
        assert response.status_code == 200

        listing = await client.get(
            "/api/v1/marketplace/bundles?status=yanked", headers=_tenant_admin_headers()
        )
        body = await listing.get_json()
        assert body["bundles"][0]["appId"] == APP_ID_A

    async def test_uninstall_unknown_is_404(self, client: Any) -> None:
        response = await client.delete(
            "/api/v1/marketplace/bundles/waddles.bot.shoutout.nope",
            headers=_platform_admin_headers(),
        )
        assert response.status_code == 404


class TestMakeAvailable:
    async def test_make_available_without_install_is_409(self, client: Any) -> None:
        """Superset invariant #1 (`available <= installed`) -- see module fail-first note."""
        response = await _make_available(client)
        assert response.status_code == 409

    async def test_make_available_no_token_is_401(self, client: Any) -> None:
        await _install(client)
        response = await client.post(
            f"/api/v1/marketplace/tenant/{TENANT_SLUG}/bundles", json={"appId": APP_ID_A}
        )
        assert response.status_code == 401

    async def test_make_available_wrong_tenant_slug_is_403(self, client: Any) -> None:
        await _install(client)
        response = await client.post(
            f"/api/v1/marketplace/tenant/{OTHER_TENANT_SLUG}/bundles",
            headers=_tenant_admin_headers(tenant=TENANT_SLUG),
            json={"appId": APP_ID_A},
        )
        assert response.status_code == 403

    async def test_make_available_success_is_201_and_listed(self, client: Any) -> None:
        await _install(client)
        response = await _make_available(client)
        assert response.status_code == 201

        listing = await client.get(
            f"/api/v1/marketplace/tenant/{TENANT_SLUG}/bundles", headers=_tenant_admin_headers()
        )
        body = await listing.get_json()
        assert body["bundles"][0]["appId"] == APP_ID_A
        assert body["bundles"][0]["available"] is True

    async def test_make_unavailable_then_list_filters_it_out(self, client: Any) -> None:
        await _install(client)
        await _make_available(client)
        response = await client.delete(
            f"/api/v1/marketplace/tenant/{TENANT_SLUG}/bundles/{APP_ID_A}",
            headers=_tenant_admin_headers(),
        )
        assert response.status_code == 200

        listing = await client.get(
            f"/api/v1/marketplace/tenant/{TENANT_SLUG}/bundles?available=true",
            headers=_tenant_admin_headers(),
        )
        body = await listing.get_json()
        assert body["bundles"] == []

    async def test_make_unavailable_unknown_is_404(self, client: Any) -> None:
        response = await client.delete(
            f"/api/v1/marketplace/tenant/{TENANT_SLUG}/bundles/{APP_ID_A}",
            headers=_tenant_admin_headers(),
        )
        assert response.status_code == 404


class TestActivateDeactivate:
    async def test_activate_without_availability_is_409(self, client: Any) -> None:
        """Superset invariant #2 (`activated <= available`) -- see module fail-first note."""
        await _install(client)
        response = await _activate(client)
        assert response.status_code == 409

    async def test_activate_no_membership_is_403(self, client: Any) -> None:
        await _install(client)
        await _make_available(client)
        token = make_user_token(user_id=999, scope="", tenant=TENANT_SLUG)
        response = await client.post(
            f"/api/v1/marketplace/community/{LIFECYCLE_COMMUNITY_ID}/bundles",
            headers={"Authorization": f"Bearer {token}"},
            json={"appId": APP_ID_A},
        )
        assert response.status_code == 403

    async def test_activate_cross_tenant_community_is_403(self, client: Any) -> None:
        """Per-community IDOR -- see module fail-first note #3."""
        await _install(client)
        await _make_available(client)
        response = await _activate(client, community_id=LIFECYCLE_OTHER_COMMUNITY_ID)
        assert response.status_code == 403

    async def test_activate_success_is_201_and_listed(self, client: Any) -> None:
        await _install(client)
        await _make_available(client)
        response = await _activate(client)
        assert response.status_code == 201

        listing = await client.get(
            f"/api/v1/marketplace/community/{LIFECYCLE_COMMUNITY_ID}/bundles",
            headers=_community_admin_headers(),
        )
        body = await listing.get_json()
        assert body["bundles"][0]["appId"] == APP_ID_A
        assert body["bundles"][0]["enabled"] is True

    async def test_activate_conflicting_bundle_is_409(self, client: Any) -> None:
        await _install(client, APP_ID_A, incompatible_with=[APP_ID_B])
        await _install(client, APP_ID_B)
        await _make_available(client, APP_ID_A)
        await _make_available(client, APP_ID_B)
        first = await _activate(client, APP_ID_A)
        assert first.status_code == 201
        second = await _activate(client, APP_ID_B)
        assert second.status_code == 409

    async def test_deactivate_success(self, client: Any) -> None:
        await _install(client)
        await _make_available(client)
        await _activate(client)
        response = await client.delete(
            f"/api/v1/marketplace/community/{LIFECYCLE_COMMUNITY_ID}/bundles/{APP_ID_A}",
            headers=_community_admin_headers(),
        )
        assert response.status_code == 200

        listing = await client.get(
            f"/api/v1/marketplace/community/{LIFECYCLE_COMMUNITY_ID}/bundles?enabled=true",
            headers=_community_admin_headers(),
        )
        body = await listing.get_json()
        assert body["bundles"] == []

    async def test_deactivate_unknown_is_404(self, client: Any) -> None:
        response = await client.delete(
            f"/api/v1/marketplace/community/{LIFECYCLE_COMMUNITY_ID}/bundles/{APP_ID_A}",
            headers=_community_admin_headers(),
        )
        assert response.status_code == 404


class TestListingFiltersAndPagination:
    async def test_list_installed_filters_by_module(self, client: Any) -> None:
        await _install(client, APP_ID_A)
        response = await client.get(
            "/api/v1/marketplace/bundles?module=social", headers=_tenant_admin_headers()
        )
        body = await response.get_json()
        assert body["bundles"] == []

    async def test_list_installed_pagination(self, client: Any) -> None:
        await _install(client, APP_ID_A)
        await _install(client, APP_ID_B)
        response = await client.get(
            "/api/v1/marketplace/bundles?page=1&limit=1", headers=_tenant_admin_headers()
        )
        body = await response.get_json()
        assert len(body["bundles"]) == 1
        assert body["pagination"] == {"page": 1, "limit": 1, "total": 2, "totalPages": 2}


class TestResolvedBundles:
    async def test_resolved_no_membership_is_403(self, client: Any) -> None:
        token = make_user_token(user_id=999, scope="", tenant=TENANT_SLUG)
        response = await client.get(
            f"/api/v1/marketplace/community/{LIFECYCLE_COMMUNITY_ID}/resolved",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_resolved_returns_activated_app_no_conflicts(self, client: Any) -> None:
        await _install(client)
        await _make_available(client)
        await _activate(client)
        response = await client.get(
            f"/api/v1/marketplace/community/{LIFECYCLE_COMMUNITY_ID}/resolved",
            headers=_community_admin_headers(),
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert [a["appId"] for a in body["apps"]] == [APP_ID_A]
        assert body["conflicts"] == []

    async def test_resolved_surfaces_conflict_between_activated_and_available(
        self, client: Any
    ) -> None:
        """B is only tenant-available (never activated) but still resolves tenant-wide.

        Activating A and B together is blocked at write time (409, see
        `test_activate_conflicting_bundle_is_409`) -- this proves the
        RESOLVED view still surfaces an emergent conflict when A is
        community-activated and B reaches the same community only via the
        tenant-wide "available" fallback (`DBInstallationLookup`'s own
        documented interpretation, see its module docstring).
        """
        await _install(client, APP_ID_A, incompatible_with=[APP_ID_B])
        await _install(client, APP_ID_B)
        await _make_available(client, APP_ID_A)
        await _make_available(client, APP_ID_B)
        await _activate(client, APP_ID_A)

        response = await client.get(
            f"/api/v1/marketplace/community/{LIFECYCLE_COMMUNITY_ID}/resolved",
            headers=_community_admin_headers(),
        )
        assert response.status_code == 200
        body = await response.get_json()
        app_ids = {a["appId"] for a in body["apps"]}
        assert app_ids == {APP_ID_A, APP_ID_B}
        assert {"appId": APP_ID_A, "conflictsWithAppId": APP_ID_B} in body["conflicts"]


class TestCrossTenantIsolation:
    """Confirms `LIFECYCLE_OTHER_TENANT_ID`/`LIFECYCLE_OTHER_COMMUNITY_ID` are genuinely isolated."""

    async def test_other_tenant_cannot_see_first_tenants_availability(self, client: Any) -> None:
        await _install(client)
        await _make_available(client)
        response = await client.get(
            f"/api/v1/marketplace/tenant/{OTHER_TENANT_SLUG}/bundles",
            headers=_tenant_admin_headers(tenant=OTHER_TENANT_SLUG),
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["bundles"] == []
