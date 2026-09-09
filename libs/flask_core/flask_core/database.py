"""
Async PyDAL Database Wrapper
=============================

Provides async wrapper around PyDAL for non-blocking database operations.
Supports connection pooling, read replicas, and transaction management.

PyDAL never auto-commits. Every method below ends the transaction it opened
(commit on success, rollback on failure) inside the SAME executor job that
ran the statement, before returning -- both because an uncommitted write
silently rolls back once its connection is returned to the pool (#280's
`action_dispatch_log` 0-rows symptom: inserts succeeded, nothing persisted),
and because a SELECT with no commit/rollback afterward leaves that
connection idle-in-transaction, poisoning it for whoever reuses it next.
Doing this in the closure that ran the statement (not a later, separate
`run_in_executor()` submission) matters: pydal connections are thread-local
(`pydal.connection.ConnectionPool`), and `ThreadPoolExecutor` does not
guarantee two submissions run on the same worker thread -- see
`transaction_async()`'s docstring for the cross-thread hazard that bit
`hub_api/services/token_billing_service.py` when it tried exactly that.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any

# Field is exported via DAL but imported here for module users
from pydal import (
    DAL,
    Field,  # noqa: F401
)

logger = logging.getLogger(__name__)


class AsyncDAL:
    """
    Async wrapper for PyDAL database operations.

    Uses ThreadPoolExecutor to run blocking PyDAL operations
    in a thread pool, allowing async/await syntax without blocking
    the event loop.
    """

    def __init__(
        self,
        uri: str,
        pool_size: int = 10,
        folder: str | None = None,
        migrate: bool = True,
        fake_migrate: bool = False,
        read_replica_uri: str | None = None,
    ):
        """
        Initialize AsyncDAL with connection details.

        Args:
            uri: Database connection string (primary/write)
            pool_size: Connection pool size
            folder: Folder for database files
            migrate: Enable automatic migrations
            fake_migrate: Enable fake migrations
            read_replica_uri: Optional read replica connection string
        """
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.migrate = migrate
        self.fake_migrate = fake_migrate
        self.read_replica_uri = read_replica_uri

        # Primary DAL (write operations)
        self.dal = DAL(
            uri,
            pool_size=pool_size,
            folder=folder,
            migrate=migrate,
            fake_migrate=fake_migrate,
            lazy_tables=True,
        )

        # Read replica DAL (read operations)
        self.read_dal = None
        if read_replica_uri:
            self.read_dal = DAL(
                read_replica_uri,
                pool_size=pool_size,
                folder=folder,
                migrate=False,  # Never migrate on read replica
                fake_migrate=False,
                lazy_tables=True,
            )

        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(
            max_workers=pool_size, thread_name_prefix="async_dal_"
        )

        logger.info(f"AsyncDAL initialized with pool_size={pool_size}")
        if read_replica_uri:
            logger.info("Read replica configured for query distribution")

    def define_table(self, *args, **kwargs):
        """Define table on primary DAL (for migrations)"""
        table = self.dal.define_table(*args, **kwargs)

        # Also define on read replica if exists
        if self.read_dal:
            self.read_dal.define_table(*args, **kwargs)

        return table

    async def select_async(self, query, *args, **kwargs):
        """
        Async select operation using read replica if available.

        PyDAL does not auto-commit, and PostgreSQL opens a transaction on
        the first statement of a connection -- a SELECT with no commit or
        rollback afterward leaves that connection idle-in-transaction when
        it's returned to the pool, poisoning it for whichever request
        reuses it next (see AsyncDAL's module docstring / #280). Every
        select ends its own transaction (commit on success, rollback on
        failure) against `query.db`, the actual DAL the query is bound to
        (primary or read replica), before returning.

        Args:
            query: PyDAL query object
            *args, **kwargs: Additional select arguments

        Returns:
            Rows object with query results
        """
        loop = asyncio.get_event_loop()

        def _select():
            try:
                result = query.select(*args, **kwargs)
                query.db.commit()
                return result
            except Exception as e:
                logger.error(f"Select error: {e}")
                query.db.rollback()
                raise

        return await loop.run_in_executor(self.executor, _select)

    async def insert_async(self, table, **fields):
        """
        Async insert operation on primary DAL.

        PyDAL does not auto-commit -- without an explicit commit the insert
        rolls back the moment the connection is returned to the pool (or
        reused by another request), so the row never actually persists even
        though `insert()` itself raised nothing (#280). Commits on success,
        rolls back on failure, in the SAME executor job that ran the insert
        so it acts on that job's own thread-local connection.

        Args:
            table: PyDAL table object
            **fields: Field values to insert

        Returns:
            Inserted record ID
        """
        loop = asyncio.get_event_loop()

        def _insert():
            try:
                result = table.insert(**fields)
                self.dal.commit()
                return result
            except Exception as e:
                logger.error(f"Insert error: {e}")
                self.dal.rollback()
                raise

        return await loop.run_in_executor(self.executor, _insert)

    async def update_async(self, query, **update_fields):
        """
        Async update operation on primary DAL.

        Commits on success, rolls back on failure, in the same executor job
        that ran the update -- see `insert_async`'s docstring for why an
        uncommitted write silently vanishes (#280).

        Args:
            query: PyDAL query object
            **update_fields: Fields to update

        Returns:
            Number of records updated
        """
        loop = asyncio.get_event_loop()

        def _update():
            try:
                result = self.dal(query).update(**update_fields)
                self.dal.commit()
                return result
            except Exception as e:
                logger.error(f"Update error: {e}")
                self.dal.rollback()
                raise

        return await loop.run_in_executor(self.executor, _update)

    async def delete_async(self, query):
        """
        Async delete operation on primary DAL.

        Commits on success, rolls back on failure, in the same executor job
        that ran the delete -- see `insert_async`'s docstring for why an
        uncommitted write silently vanishes (#280).

        Args:
            query: PyDAL query object

        Returns:
            Number of records deleted
        """
        loop = asyncio.get_event_loop()

        def _delete():
            try:
                result = self.dal(query).delete()
                self.dal.commit()
                return result
            except Exception as e:
                logger.error(f"Delete error: {e}")
                self.dal.rollback()
                raise

        return await loop.run_in_executor(self.executor, _delete)

    async def count_async(self, query):
        """
        Async count operation using read replica if available.

        Ends its own transaction (commit on success, rollback on failure)
        against whichever DAL actually ran the count -- see `select_async`'s
        docstring for why a dangling SELECT transaction poisons the pooled
        connection (#280).

        Args:
            query: PyDAL query object

        Returns:
            Count of records matching query
        """
        loop = asyncio.get_event_loop()
        dal = self.read_dal if self.read_dal else self.dal

        def _count():
            try:
                result = dal(query).count()
                dal.commit()
                return result
            except Exception as e:
                logger.error(f"Count error: {e}")
                dal.rollback()
                raise

        return await loop.run_in_executor(self.executor, _count)

    async def executesql_async(self, sql: str, params: list | None = None):
        """
        Execute raw SQL asynchronously.

        Raw SQL may be a read or a write, so it gets the same treatment as
        both: commit on success, rollback on failure, in the same executor
        job that ran the statement (#280).

        Args:
            sql: SQL query string
            params: Optional query parameters

        Returns:
            Query results
        """
        loop = asyncio.get_event_loop()

        def _execute():
            try:
                result = self.dal.executesql(sql, placeholders=params)
                self.dal.commit()
                return result
            except Exception as e:
                logger.error(f"ExecuteSQL error: {e}")
                self.dal.rollback()
                raise

        return await loop.run_in_executor(self.executor, _execute)

    async def execute(self, sql: str, params: list | None = None):
        """
        Execute raw SQL with parameter binding using adapter directly.

        Converts $N placeholders to %s for psycopg2 compatibility.

        Args:
            sql: SQL query string with $1, $2, $3... placeholders
            params: Optional query parameters as list

        Returns:
            Query results as list of Row objects (dict-like)
        """
        loop = asyncio.get_event_loop()

        def _execute():
            try:
                # Convert $N placeholders to %s for psycopg2
                if params:
                    converted_sql = sql
                    for i in range(len(params), 0, -1):
                        converted_sql = converted_sql.replace(f"${i}", "%s")

                    # Convert special types for psycopg2
                    import json as json_module
                    from uuid import UUID

                    converted_params = []
                    for param in params:
                        if isinstance(param, UUID):
                            converted_params.append(str(param))
                        elif isinstance(param, (dict, list)):
                            # Convert dicts/lists to JSON strings for JSONB columns
                            converted_params.append(json_module.dumps(param))
                        else:
                            converted_params.append(param)
                    params_tuple = tuple(converted_params)
                else:
                    converted_sql = sql
                    params_tuple = None

                # Execute using adapter directly
                self.dal._adapter.execute(converted_sql, params_tuple)

                # Fetch results
                try:
                    result = self.dal._adapter.cursor.fetchall()
                except Exception:  # noqa: BLE001 -- "no results" raises a
                    # different, driver-specific exception type per DB-API
                    # backend (sqlite3 vs psycopg2 vs ...) this multi-backend
                    # adapter supports; narrowing to one backend's exception
                    # type would break the others.
                    # No results to fetch (e.g., INSERT/UPDATE without RETURNING)
                    result = []

                # Convert to list of dicts for consistency
                if result and self.dal._adapter.cursor.description:
                    columns = [desc[0] for desc in self.dal._adapter.cursor.description]
                    rows = [dict(zip(columns, row)) for row in result]
                else:
                    rows = []

                # Commit so a write via raw SQL actually persists, and a
                # read doesn't leave the connection idle-in-transaction
                # when it's returned to the pool (#280).
                self.dal.commit()
                return rows

            except Exception as e:
                logger.error(f"Execute error: {e}")
                self.dal.rollback()
                raise

        return await loop.run_in_executor(self.executor, _execute)

    @asynccontextmanager
    async def transaction_async(self):
        """
        Async context manager for database transactions.

        CAUTION -- does NOT provide cross-call atomicity. Every write
        method on this class (`insert_async`/`update_async`/`delete_async`/
        `bulk_insert_async`/`execute`/`executesql_async`) now commits
        inside its own executor job as of #280's fix, so by the time this
        context manager's own commit/rollback runs (a SEPARATE executor
        submission, possibly on a different pool thread and against a
        different thread-local pydal connection than the ones the writes
        inside the `async with` block ran on) there is nothing left
        pending to commit, and nothing left to roll back if a later
        statement in the block fails -- earlier statements already
        persisted. `hub_api/services/token_billing_service.py` and
        `marketplace_lifecycle_service.py` hit this exact class of bug
        independently and worked around it by bundling an entire
        read-modify-write + `dal.commit()` into ONE synchronous function
        submitted as a single `run_in_executor()` job (no `await` in the
        middle) -- follow that pattern for anything needing multi-statement
        atomicity, not this context manager.

        Usage:
            async with dal.transaction_async():
                await dal.insert_async(table, field1='value1')
                await dal.update_async(query, field2='value2')
        """
        loop = asyncio.get_event_loop()

        # Begin transaction
        await loop.run_in_executor(self.executor, lambda: None)

        try:
            yield self
            # Commit transaction
            await loop.run_in_executor(self.executor, self.dal.commit)
        except Exception as e:
            # Rollback on error
            await loop.run_in_executor(self.executor, self.dal.rollback)
            logger.error(f"Transaction rolled back: {e}")
            raise

    async def bulk_insert_async(self, table, records: list[dict[str, Any]]):
        """
        Bulk insert records asynchronously.

        Commits on success, rolls back on failure, in the same executor job
        that ran the insert -- see `insert_async`'s docstring for why an
        uncommitted write silently vanishes (#280).

        Args:
            table: PyDAL table object
            records: List of dictionaries with field values

        Returns:
            List of inserted record IDs
        """
        loop = asyncio.get_event_loop()

        def _bulk_insert():
            try:
                result = table.bulk_insert(records)
                self.dal.commit()
                return result
            except Exception as e:
                logger.error(f"Bulk insert error: {e}")
                self.dal.rollback()
                raise

        return await loop.run_in_executor(self.executor, _bulk_insert)

    async def close_async(self):
        """Close database connections and thread pool"""
        loop = asyncio.get_event_loop()

        def _close():
            self.dal.close()
            if self.read_dal:
                self.read_dal.close()

        await loop.run_in_executor(self.executor, _close)
        self.executor.shutdown(wait=True)
        logger.info("AsyncDAL connections closed")

    def __getattr__(self, name):
        """Proxy attribute access to underlying DAL"""
        return getattr(self.dal, name)


def _convert_uri_for_pydal(uri: str) -> str:
    """Convert postgresql:// to postgres:// for PyDAL compatibility."""
    if uri and uri.startswith("postgresql://"):
        return uri.replace("postgresql://", "postgres://", 1)
    return uri


def init_database(
    uri: str,
    pool_size: int = 10,
    read_replica_uri: str | None = None,
    folder: str | None = None,
    migrate: bool = True,
) -> AsyncDAL:
    """
    Initialize database with AsyncDAL wrapper.

    Args:
        uri: Primary database connection string
        pool_size: Connection pool size
        read_replica_uri: Optional read replica connection string
        folder: Folder for database files
        migrate: Enable automatic migrations

    Returns:
        Configured AsyncDAL instance
    """
    # Convert postgresql:// to postgres:// for PyDAL compatibility
    converted_uri = _convert_uri_for_pydal(uri)
    converted_replica = (
        _convert_uri_for_pydal(read_replica_uri) if read_replica_uri else None
    )

    return AsyncDAL(
        uri=converted_uri,
        pool_size=pool_size,
        folder=folder,
        migrate=migrate,
        read_replica_uri=converted_replica,
    )
