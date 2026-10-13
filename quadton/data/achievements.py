from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AchievementDef:
    achievement_id: str
    name: str
    description: str
    stat_field: str | None  # column in user_stats, if applicable
    target: int
    reward_qc: int
    repeatable: bool = False


ACHIEVEMENTS: tuple[AchievementDef, ...] = (
    AchievementDef("first_job", "First Day", "Complete your first job.",
                   "jobs_completed", 1, 100),
    AchievementDef("hustler", "Hustler", "Complete 100 jobs.",
                   "jobs_completed", 100, 2000),
    AchievementDef("angler", "Angler", "Catch 50 fish.",
                   "fish_caught", 50, 750),
    AchievementDef("prospector", "Prospector", "Mine 50 times.",
                   "ores_mined", 50, 750),
    AchievementDef("treasure_hunter", "Treasure Hunter", "Find 25 treasures.",
                   "treasures_found", 25, 900),
)


def by_id(aid: str) -> AchievementDef | None:
    for a in ACHIEVEMENTS:
        if a.achievement_id == aid:
            return a
    return None
