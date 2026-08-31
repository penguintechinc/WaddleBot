"""`blueprints/v1/community_inventory.py` -- admin item CRUD + member checkout/checkin.

Also proves the checkout/checkin bug fix documented in
`services/community_inventory.py`'s module docstring: a real
`inventory_checkouts` row is created on checkout (Node's equivalent
never wrote one -- see that docstring for the parameter-order bug this
port fixes instead of reproducing).
"""

from __future__ import annotations

import json as json_module
from typing import Any

import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints.v1.community_inventory import inventory_bp
from services import community_inventory as inventory_svc


@pytest.fixture
def app(community_db: Any) -> Quart:
    dal, _ = community_db
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(inventory_bp)
    quart_app.config["dal"] = dal
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


async def _post_json(
    client: Any, path: str, headers: dict[str, str], payload: dict[str, Any]
) -> Any:
    return await client.post(
        path,
        headers={**headers, "Content-Type": "application/json"},
        data=json_module.dumps(payload),
    )


class TestScopeAndTenant:
    async def test_wrong_scope_is_403(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        response = await client.get(
            f"/api/v1/admin/{community_id}/inventory/items",
            headers=auth_headers(scope="community.inventory:use"),
        )
        assert response.status_code == 403

    async def test_unknown_community_is_404(self, client: Any, auth_headers: Any) -> None:
        response = await client.get(
            "/api/v1/admin/9999/inventory/items",
            headers=auth_headers(scope="community.inventory:read"),
        )
        assert response.status_code == 404


class TestItemCrud:
    async def test_create_item_requires_name(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        response = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/inventory/items",
            auth_headers(scope="community.inventory:write"),
            {"name": "", "quantity": 5},
        )
        assert response.status_code == 400

    async def test_create_list_update_delete_item(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        write_headers = auth_headers(scope="community.inventory:write")

        create_resp = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/inventory/items",
            write_headers,
            {"name": "Green Screen", "category": "gear", "quantity": 3},
        )
        assert create_resp.status_code == 201
        item = (await create_resp.get_json())["item"]
        assert item["quantity"] == 3
        assert item["available_quantity"] == 3
        item_id = item["id"]

        list_resp = await client.get(
            f"/api/v1/admin/{community_id}/inventory/items",
            headers=auth_headers(scope="community.inventory:read"),
        )
        assert len((await list_resp.get_json())["items"]) == 1

        update_resp = await client.put(
            f"/api/v1/admin/{community_id}/inventory/items/{item_id}",
            headers={**write_headers, "Content-Type": "application/json"},
            data=json_module.dumps({"name": "Green Screen Mk2"}),
        )
        assert update_resp.status_code == 200
        assert (await update_resp.get_json())["item"]["name"] == "Green Screen Mk2"

        delete_resp = await client.delete(
            f"/api/v1/admin/{community_id}/inventory/items/{item_id}", headers=write_headers
        )
        assert delete_resp.status_code == 200

        after_delete = await client.get(
            f"/api/v1/admin/{community_id}/inventory/items",
            headers=auth_headers(scope="community.inventory:read"),
        )
        assert len((await after_delete.get_json())["items"]) == 0


def _fake_stock_fn(
    dal: Any,
    fn_name: str,
    item_id: int,
    quantity: int,
    user_id: int,
    community_id: int,
    note: str | None,
) -> tuple[bool, str]:
    """Stand-in for `_run_stock_fn`'s call to the real Postgres `*_inventory_stock` functions.

    See `config/postgres/migrations/014_add_quartermaster_tables.sql` --
    sqlite:memory has no stored-function support. Applies the same
    available_quantity delta the real function would, so checkout/checkin's
    surrounding logic (item lookup, checkout row lifecycle -- the actual
    behavior this port fixes, per the module docstring) is still exercised
    against a real row.
    """
    delta = -quantity if fn_name == "remove_inventory_stock" else quantity
    item = dal.inventory_items[item_id]
    dal(dal.inventory_items.id == item_id).update(
        available_quantity=item.available_quantity + delta
    )
    dal.commit()
    return True, "ok"


class TestCheckoutCheckin:
    async def test_checkout_creates_a_real_checkout_row(
        self, client: Any, auth_headers: Any, community_db: Any, monkeypatch: Any
    ) -> None:
        """Regression coverage for the Node bug fixed during this port.

        See `services/community_inventory.py`'s module docstring.
        """
        monkeypatch.setattr(inventory_svc, "_run_stock_fn", _fake_stock_fn)
        dal, community_id = community_db
        create_resp = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/inventory/items",
            auth_headers(scope="community.inventory:write"),
            {"name": "Boom Mic", "quantity": 2},
        )
        item_id = (await create_resp.get_json())["item"]["id"]

        checkout_resp = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/inventory/checkout",
            auth_headers(scope="community.inventory:use", user_id="1"),
            {"item_id": item_id, "quantity": 1},
        )
        assert checkout_resp.status_code == 201
        checkout = (await checkout_resp.get_json())["checkout"]
        assert checkout["status"] == "active"
        assert dal(dal.inventory_checkouts.id == checkout["id"]).count() == 1
        assert dal.inventory_items[item_id].available_quantity == 1

        my_items_resp = await client.get(
            f"/api/v1/admin/{community_id}/inventory/my-items",
            headers=auth_headers(scope="community.inventory:use", user_id="1"),
        )
        assert len((await my_items_resp.get_json())["checkouts"]) == 1

        checkin_resp = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/inventory/checkin",
            auth_headers(scope="community.inventory:use", user_id="1"),
            {"checkout_id": checkout["id"]},
        )
        assert checkin_resp.status_code == 200
        assert (await checkin_resp.get_json())["checkout"]["status"] == "returned"
        assert dal.inventory_items[item_id].available_quantity == 2

    async def test_checkout_insufficient_quantity_is_409(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        create_resp = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/inventory/items",
            auth_headers(scope="community.inventory:write"),
            {"name": "Rare Lens", "quantity": 1},
        )
        item_id = (await create_resp.get_json())["item"]["id"]

        response = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/inventory/checkout",
            auth_headers(scope="community.inventory:use", user_id="1"),
            {"item_id": item_id, "quantity": 5},
        )
        assert response.status_code == 409
