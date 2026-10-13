from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Awaitable, Callable

import aiosqlite

from quadton.db.database import Database


@dataclass
class CooldownStatus:
    ready: bool
    remaining: int  # seconds


GrantCallback = Callable[[aiosqlite.Connection], Awaitable[None]]


class CooldownService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def check(self, user_id: int, key: str) -> CooldownStatus:
        row = await self.db.fetchone(
            "SELECT ready_at FROM cooldowns WHERE user_id=? AND key=?",
            (user_id, key),
        )
        if row is None:
            return CooldownStatus(True, 0)
        remaining = int(row[0]) - int(time.time())
        return CooldownStatus(remaining <= 0, max(0, remaining))

    async def reward_with_cooldown(
        self,
        user_id: int,
        key: str,
        duration: int,
        grant: GrantCallback,
    ) -> CooldownStatus:
        """Atomically check cooldown, run `grant(conn)`, then start the cooldown.

        Any exception rolls back all three operations.
        """
        now = int(time.time())
        async with self.db.transaction() as conn:
            cur = await conn.execute(
                "SELECT ready_at FROM cooldowns WHERE user_id=? AND key=?",
                (user_id, key),
            )
            row = await cur.fetchone()
            if row is not None and int(row[0]) > now:
                return CooldownStatus(False, int(row[0]) - now)
            await grant(conn)
            await conn.execute(
                """
                INSERT INTO cooldowns(user_id, key, ready_at) VALUES (?, ?, ?)
                ON CONFLICT(user_id, key) DO UPDATE SET ready_at=excluded.ready_at
                """,
                (user_id, key, now + duration),
            )
        return CooldownStatus(True, 0)

    async def set(self, user_id: int, key: str, duration: int) -> None:
        async with self.db.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO cooldowns(user_id, key, ready_at) VALUES (?, ?, ?)
                ON CONFLICT(user_id, key) DO UPDATE SET ready_at=excluded.ready_at
                """,
                (user_id, key, int(time.time()) + duration),
            )

    async def clear(self, user_id: int, key: str) -> None:
        async with self.db.transaction() as conn:
            await conn.execute(
                "DELETE FROM cooldowns WHERE user_id=? AND key=?", (user_id, key)
            )
