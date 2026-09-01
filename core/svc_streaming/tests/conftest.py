"""Shared fixtures for svc-streaming's tests.

svc_streaming isn't installed as a package (a standalone control-plane
directory run via `hypercorn app:app`, same shape as `core/
svc_presentation`) -- its own directory has to be put on `sys.path`
explicitly for `from app import create_app` / `import config` to resolve.

`test_config`/`built_app` build a real `Quart` app against a file-backed
sqlite DB (`tmp_path`-scoped -- `AsyncDAL`'s `ThreadPoolExecutor` opens a
connection per worker thread; `sqlite:memory` is connection-scoped and a
worker thread would see a blank DB, the same gotcha `core/svc_presentation/
tests/conftest.py`'s own fixture documents) with `db_migrate=True` so
`bind_streaming_tables()`/`bind_shared_read_tables()` issue real DDL.

The app's `FFMPEG_SUPERVISOR` is swapped for one backed by
`tests.fakes.FakeSubprocessExec` immediately after `create_app()` builds
it and before the test client enters -- every `/start` route in these
tests exercises the REAL `FFmpegSupervisor`/`build_ffmpeg_args()` logic,
just never spawns a real OS process.
"""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from flask_core.auth import create_jwt_token
from quart.typing import TestClientProtocol

from app import create_app
from config import Config
from services.ffmpeg_engine import FFmpegSupervisor
from services.schema import bind_shared_read_tables
from tests.fakes import FakeSubprocessExec

SECRET_KEY = "change-me-in-production"
TENANT_SLUG = "acme-corp"
OTHER_TENANT_SLUG = "other-corp"


@pytest.fixture
def test_config(tmp_path: Path) -> Config:
    """A `Config` pointed at an ephemeral, migrated sqlite file DB."""
    db_path = tmp_path / "svc_streaming_test.db"
    recordings_dir = tmp_path / "recordings"
    return Config(
        module_name="svc-streaming",
        module_version="test",
        module_port=8208,
        pipeline_stage="streaming",
        log_level="INFO",
        database_url=f"sqlite://{db_path}",
        db_pool_size=1,
        db_migrate=True,
        hub_api_url="http://hub-api-test.invalid:8204",
        jwt_secret_key=SECRET_KEY,
        ffmpeg_binary="ffmpeg",
        recordings_dir=str(recordings_dir),
        transcode_token_cost=5,
        transcode_product_key="transcoding_minutes",
        twitch_client_id="",
        twitch_client_secret="",
        youtube_api_key="",
    )


@pytest_asyncio.fixture
async def app_and_client(test_config: Config) -> AsyncIterator[tuple[Any, TestClientProtocol]]:
    """A running svc-streaming app (startup/shutdown fired), fake ffmpeg exec, + test client."""
    os.environ["SECRET_KEY"] = SECRET_KEY  # community_access._is_super_admin reads this directly
    app = create_app(test_config)
    app.config["FFMPEG_SUPERVISOR"] = FFmpegSupervisor(subprocess_exec=FakeSubprocessExec())
    async with app.test_app() as running:
        yield app, running.test_client()


@pytest_asyncio.fixture
async def client(app_and_client: tuple[Any, TestClientProtocol]) -> TestClientProtocol:
    """Just the test client half of `app_and_client`, for tests that don't need `app`."""
    return app_and_client[1]


@pytest.fixture
def fake_subprocess(app_and_client: tuple[Any, TestClientProtocol]) -> FakeSubprocessExec:
    """The `FakeSubprocessExec` backing the running app's `FFMPEG_SUPERVISOR`."""
    app, _ = app_and_client
    supervisor: FFmpegSupervisor = app.config["FFMPEG_SUPERVISOR"]
    return supervisor._subprocess_exec  # noqa: SLF001 - test-only introspection


@pytest.fixture
def dal_pair(app_and_client: tuple[Any, TestClientProtocol]) -> tuple[Any, Any]:
    """`(async_dal, dal)` from the running app -- for direct seeding/assertions."""
    app, _ = app_and_client
    return app.config["async_dal"], app.config["dal"]


def seed_tenant(dal: Any, *, slug: str = TENANT_SLUG) -> int:
    """Insert one active `tenants` row; returns its id."""
    bind_shared_read_tables(dal, migrate=True)
    tenant_id: int = dal.tenants.insert(slug=slug, is_active=True)
    dal.commit()
    return tenant_id


def seed_community(dal: Any, *, tenant_id: int) -> int:
    """Insert one `communities` row scoped to `tenant_id`; returns its id."""
    bind_shared_read_tables(dal, migrate=True)
    community_id: int = dal.communities.insert(tenant_id=tenant_id)
    dal.commit()
    return community_id


def seed_membership(
    dal: Any, *, community_id: int, user_id: int, role: str = "community-owner"
) -> None:
    """Insert one active `community_members` row -- `user_id` stored as `str()`, matching prod."""
    bind_shared_read_tables(dal, migrate=True)
    dal.community_members.insert(
        community_id=community_id, user_id=str(user_id), role=role, is_active=True
    )
    dal.commit()


def seed_connected_channel(
    dal: Any,
    *,
    community_id: int,
    platform: str,
    platform_server_id: str,
    platform_server_name: str | None = None,
    status: str = "approved",
) -> None:
    """Insert one `community_servers` row -- real data `services/live_channels_service.py` reads."""
    bind_shared_read_tables(dal, migrate=True)
    dal.community_servers.insert(
        community_id=community_id,
        platform=platform,
        platform_server_id=platform_server_id,
        platform_server_name=platform_server_name,
        status=status,
    )
    dal.commit()


def seed_token_product(
    dal: Any,
    *,
    key: str = "transcoding_minutes",
    name: str = "Transcoding Minutes",
    unit: str = "minute",
    price_cents: int = 100,
    tokens_granted: int = 60,
    active: bool = True,
) -> None:
    """Insert one `token_products` row -- mirrors migration 078's seed for local test DBs.

    svc-streaming's own DB never actually owns `token_products` (that's
    hub-api's table, migration 076) -- tests that need it define a
    minimal local copy so `services.token_ledger_client`'s HTTP-mocked
    tests have something to assert against without a real hub-api.
    """
    if "token_products" not in dal.tables:
        from pydal import Field

        dal.define_table(
            "token_products",
            Field("key", "string", unique=True),
            Field("name", "string"),
            Field("unit", "string"),
            Field("price_cents", "integer"),
            Field("tokens_granted", "integer"),
            Field("active", "boolean", default=True),
            migrate=True,
        )
    dal.token_products.insert(
        key=key,
        name=name,
        unit=unit,
        price_cents=price_cents,
        tokens_granted=tokens_granted,
        active=active,
    )
    dal.commit()


def make_user_token(
    *, user_id: int, tenant: str = TENANT_SLUG, roles: list[str] | None = None, scope: str = ""
) -> str:
    """Mint a real JWT whose `sub` matches a seeded `community_members.user_id`."""
    return create_jwt_token(
        user_id=str(user_id),
        username="alice",
        email="alice@example.com",
        roles=roles or [],
        secret_key=SECRET_KEY,
        tenant=tenant,
        scope=scope,
    )


def make_super_admin_token(*, user_id: int = 999, tenant: str = TENANT_SLUG) -> str:
    """Mint a JWT with `roles=["super_admin"]` -- bypasses `community_access` checks."""
    return create_jwt_token(
        user_id=str(user_id),
        username="root",
        email="root@example.com",
        roles=["super_admin"],
        secret_key=SECRET_KEY,
        tenant=tenant,
    )


def auth_header(token: str) -> dict[str, str]:
    """`{"Authorization": "Bearer <token>"}` -- the one header every protected route needs."""
    return {"Authorization": f"Bearer {token}"}
