from __future__ import annotations

import time

import aiosqlite

from quadton.db.database import Database

ECONOMIC = "economic"
ACTIVITY = "activity"


class EffectService:
    """Active buffs. Stacking rule: at most one economic and one activity effect."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def active_effects(self, user_id: int) -> list[dict]:
        now = int(time.time())
        rows = await self.db.fetchall(
            """
            SELECT effect_id, effect_type, perk_class, strength, source,
                   activated_at, expires_at
            FROM effects
            WHERE user_id=? AND expires_at > ?
            ORDER BY expires_at ASC
            """,
            (user_id, now),
        )
        return [dict(r) for r in rows]

    async def apply(
        self,
        conn: aiosqlite.Connection,
        user_id: int,
        effect_type: str,
        perk_class: str,
        strength: float,
        source: str,
        duration: int,
    ) -> None:
        if perk_class not in (ECONOMIC, ACTIVITY):
            raise ValueError("invalid perk_class")
        now = int(time.time())
        # Enforce one effect per perk_class (stacking policy).
        await conn.execute(
            "DELETE FROM effects WHERE user_id=? AND perk_class=?",
            (user_id, perk_class),
        )
        await conn.execute(
            """
            INSERT INTO effects(user_id, effect_type, perk_class, strength, source,
                                activated_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, effect_type, perk_class, float(strength), source, now,
             now + int(duration)),
        )

    async def multiplier(self, user_id: int, effect_type: str) -> float:
        now = int(time.time())
        row = await self.db.fetchone(
            """
            SELECT strength FROM effects
            WHERE user_id=? AND effect_type=? AND expires_at > ?
            LIMIT 1
            """,
            (user_id, effect_type, now),
        )
        if row is None:
            return 1.0
        return 1.0 + float(row[0])

    async def purge_expired(self) -> int:
        async with self.db.transaction() as conn:
            cur = await conn.execute(
                "DELETE FROM effects WHERE expires_at <= ?", (int(time.time()),)
            )
            return cur.rowcount
