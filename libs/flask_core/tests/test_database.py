"""AsyncDAL commit/rollback regression tests -- #280.

Before this fix, `AsyncDAL.insert_async()`/`update_async()`/`delete_async()`/
`bulk_insert_async()`/`execute()`/`executesql_async()` never called
`dal.commit()`, and `select_async()`/`count_async()` never ended their own
read transaction either. PyDAL does not auto-commit, so an uncommitted
write is invisible to any other connection the moment the writer's own
connection is returned to the pool or reused -- exactly the
`action_dispatch_log` "0 rows despite dozens of live dispatches" symptom.

`TestInsertAsyncPersists` reproduces that class of bug directly: it opens a
SEPARATE, independent `sqlite3` connection to the same on-disk DB file (not
`AsyncDAL`'s own thread-local pooled connection) and proves the inserted
row is durably visible there -- something only a real `commit()` achieves.
Verified fail-first: reverting `insert_async()` to the pre-fix body (no
`self.dal.commit()`) makes `test_insert_async_row_is_visible_to_a_fresh_independent_connection`
fail with an empty result set.

`TestSelectAsyncEndsItsTransaction` covers the read side (`select_async`)
the same class of bug affects: PostgreSQL opens a transaction on the first
statement of a connection (unlike SQLite, which only does so before DML),
so a SELECT with no commit/rollback afterward leaves that connection
idle-in-transaction when pooled -- poisoning it for whoever reuses it next.
SQLite can't reproduce the idle-in-transaction *symptom* itself (its
`sqlite3.Connection.in_transaction` never flips true for a bare SELECT), so
this asserts the code-level contract our fix guarantees instead: every
`select_async()` call ends its own transaction by calling `commit()` on
success or `rollback()` on failure, against `query.db` -- the actual DAL
the query is bound to.
"""

from __future__ import annotations

import sqlite3
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

_PKG_DIR = Path(__file__).resolve().parent.parent / "flask_core"
if "flask_core" not in sys.modules:
    _stub = types.ModuleType("flask_core")
    _stub.__path__ = [str(_PKG_DIR)]
    sys.modules["flask_core"] = _stub

from flask_core.database import AsyncDAL


@pytest.fixture
async def async_dal(tmp_path: Path) -> AsyncDAL:
    """A real `AsyncDAL` against an on-disk (not `:memory:`) sqlite file.

    File-backed, not in-memory: an independent `sqlite3.connect()` to the
    same path in the test body needs a real file to open a second,
    genuinely separate connection against -- `sqlite:memory:` gives every
    connection its own private, empty database regardless of commit state,
    which would make the persistence test pass even without the fix.

    No `close_async()` teardown: `close_async()` runs `self.dal.close()`
    inside a NEW `run_in_executor()` submission, but the DAL's
    `_pydal_db_instances_` registration happened in `DAL.__new__` on the
    thread that constructed it (this fixture's caller, i.e. the event
    loop thread) -- a separate, pre-existing thread-locality bug in
    `close_async()` itself, out of scope for #280's commit fix. `tmp_path`
    cleans up the on-disk file regardless.
    """
    dal = AsyncDAL(
        "sqlite://persist.db",
        folder=str(tmp_path),
        pool_size=1,
        migrate=True,
    )
    dal.define_table("widgets", dal.Field("name"))
    # `lazy_tables=True` means the physical CREATE TABLE doesn't run until
    # first real access -- force it now so tests that seed rows via a raw
    # `sqlite3` connection (bypassing AsyncDAL entirely) find the table
    # already on disk.
    await dal.count_async(dal.dal.widgets.id > 0)
    return dal


class TestInsertAsyncPersists:
    """`insert_async()` must durably commit, not just succeed in-process."""

    async def test_insert_async_row_is_visible_to_a_fresh_independent_connection(
        self, async_dal: AsyncDAL, tmp_path: Path
    ) -> None:
        await async_dal.insert_async(async_dal.dal.widgets, name="quote-1")

        db_path = tmp_path / "persist.db"
        raw = sqlite3.connect(str(db_path))
        try:
            rows = raw.execute("SELECT name FROM widgets").fetchall()
        finally:
            raw.close()

        assert rows == [("quote-1",)]

    async def test_update_async_change_is_visible_to_a_fresh_independent_connection(
        self, async_dal: AsyncDAL, tmp_path: Path
    ) -> None:
        row_id = await async_dal.insert_async(async_dal.dal.widgets, name="before")
        await async_dal.update_async(async_dal.dal.widgets.id == row_id, name="after")

        db_path = tmp_path / "persist.db"
        raw = sqlite3.connect(str(db_path))
        try:
            rows = raw.execute("SELECT name FROM widgets").fetchall()
        finally:
            raw.close()

        assert rows == [("after",)]

    async def test_delete_async_removal_is_visible_to_a_fresh_independent_connection(
        self, async_dal: AsyncDAL, tmp_path: Path
    ) -> None:
        """Row is seeded via a raw, independently-committed `sqlite3` insert
        (not `insert_async`) so this test isolates `delete_async`'s own
        commit behavior -- deleting a row that was itself never durably
        committed would show "gone" from a fresh connection regardless of
        whether `delete_async` commits, which wouldn't discriminate the bug
        this test exists to catch."""
        db_path = tmp_path / "persist.db"
        seed_conn = sqlite3.connect(str(db_path))
        try:
            cursor = seed_conn.execute("INSERT INTO widgets (name) VALUES ('doomed')")
            row_id = cursor.lastrowid
            seed_conn.commit()
        finally:
            seed_conn.close()

        await async_dal.delete_async(async_dal.dal.widgets.id == row_id)

        raw = sqlite3.connect(str(db_path))
        try:
            rows = raw.execute("SELECT name FROM widgets").fetchall()
        finally:
            raw.close()

        assert rows == []


class TestSelectAsyncEndsItsTransaction:
    """A read must end its own transaction, not leave the connection dangling."""

    async def test_select_async_commits_on_success(self, async_dal: AsyncDAL) -> None:
        await async_dal.insert_async(async_dal.dal.widgets, name="a")

        commit_spy = MagicMock(wraps=async_dal.dal.commit)
        async_dal.dal.commit = commit_spy

        await async_dal.select_async(async_dal.dal(async_dal.dal.widgets.name == "a"))

        commit_spy.assert_called_once()

    async def test_select_async_rolls_back_on_failure(
        self, async_dal: AsyncDAL
    ) -> None:
        rollback_spy = MagicMock(wraps=async_dal.dal.rollback)
        async_dal.dal.rollback = rollback_spy

        query_set: Any = async_dal.dal(async_dal.dal.widgets.name == "a")
        query_set.select = MagicMock(side_effect=RuntimeError("boom"))

        with pytest.raises(RuntimeError, match="boom"):
            await async_dal.select_async(query_set)

        rollback_spy.assert_called_once()

    async def test_count_async_commits_on_success(self, async_dal: AsyncDAL) -> None:
        await async_dal.insert_async(async_dal.dal.widgets, name="a")

        commit_spy = MagicMock(wraps=async_dal.dal.commit)
        async_dal.dal.commit = commit_spy

        count = await async_dal.count_async(async_dal.dal.widgets.name == "a")

        assert count == 1
        commit_spy.assert_called_once()
