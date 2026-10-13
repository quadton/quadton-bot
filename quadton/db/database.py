from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Sequence

import aiosqlite

log = logging.getLogger(__name__)


class Database:
    """Single-writer SQLite wrapper.

    Writes are serialized via ``_write_lock`` because SQLite permits only one
    writer at a time. Reads use the shared connection directly.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._conn: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute("PRAGMA journal_mode = WAL")
        await self._conn.execute("PRAGMA synchronous = NORMAL")
        await self._conn.execute("PRAGMA busy_timeout = 5000")
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """BEGIN IMMEDIATE — serialized writer. Not re-entrant."""
        if self._write_lock.locked():
            # Guard against accidental nesting.
            raise RuntimeError("nested transaction() is not supported")
        async with self._write_lock:
            conn = self.conn
            await conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                await conn.rollback()
                raise
            else:
                await conn.commit()

    async def execute(self, sql: str, params: Sequence[Any] = ()) -> aiosqlite.Cursor:
        return await self.conn.execute(sql, params)

    async def fetchone(
        self, sql: str, params: Sequence[Any] = ()
    ) -> aiosqlite.Row | None:
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchone()

    async def fetchall(
        self, sql: str, params: Sequence[Any] = ()
    ) -> list[aiosqlite.Row]:
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchall()

    async def integrity_check(self) -> str:
        row = await self.fetchone("PRAGMA integrity_check")
        return str(row[0]) if row else "unknown"
