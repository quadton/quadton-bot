from __future__ import annotations

import time

from quadton.data.achievements import ACHIEVEMENTS, by_id
from quadton.db.database import Database


class AchievementService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def progress(self, user_id: int) -> dict[str, dict]:
        rows = await self.db.fetchall(
            "SELECT achievement_id, progress, unlocked_at FROM user_achievements WHERE user_id=?",
            (user_id,),
        )
        stored = {r["achievement_id"]: dict(r) for r in rows}
        result = {}
        for a in ACHIEVEMENTS:
            entry = stored.get(a.achievement_id, {"progress": 0, "unlocked_at": None})
            result[a.achievement_id] = {
                "name": a.name,
                "target": a.target,
                "progress": int(entry["progress"]),
                "unlocked_at": entry["unlocked_at"],
                "reward_qc": a.reward_qc,
            }
        return result

    async def check_and_grant(self, user_id: int) -> list[str]:
        """Recompute all stat-driven achievements and grant any newly met ones.

        Returns the list of newly unlocked achievement IDs.
        """
        unlocked: list[str] = []
        stats_row = await self.db.fetchone(
            "SELECT * FROM user_stats WHERE user_id=?", (user_id,)
        )
        if stats_row is None:
            return unlocked
        stats = dict(stats_row)

        async with self.db.transaction() as conn:
            for a in ACHIEVEMENTS:
                if a.stat_field is None:
                    continue
                current = int(stats.get(a.stat_field, 0))
                cur = await conn.execute(
                    "SELECT progress, unlocked_at FROM user_achievements "
                    "WHERE user_id=? AND achievement_id=?",
                    (user_id, a.achievement_id),
                )
                row = await cur.fetchone()
                already = row is not None and row["unlocked_at"] is not None
                await conn.execute(
                    """
                    INSERT INTO user_achievements(user_id, achievement_id, progress)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id, achievement_id) DO UPDATE SET
                        progress = excluded.progress
                    """,
                    (user_id, a.achievement_id, min(current, a.target)),
                )
                if not already and current >= a.target:
                    await conn.execute(
                        "UPDATE user_achievements SET unlocked_at=? "
                        "WHERE user_id=? AND achievement_id=?",
                        (int(time.time()), user_id, a.achievement_id),
                    )
                    if a.reward_qc > 0:
                        await conn.execute(
                            "UPDATE accounts SET balance = balance + ? "
                            "WHERE user_id=? AND kind='wallet'",
                            (a.reward_qc, user_id),
                        )
                        await conn.execute(
                            "UPDATE users SET lifetime_earned = lifetime_earned + ? "
                            "WHERE user_id=?",
                            (a.reward_qc, user_id),
                        )
                    unlocked.append(a.achievement_id)
        return unlocked

    async def count_unlocked(self, user_id: int) -> int:
        row = await self.db.fetchone(
            "SELECT COUNT(*) FROM user_achievements "
            "WHERE user_id=? AND unlocked_at IS NOT NULL",
            (user_id,),
        )
        return int(row[0]) if row else 0
