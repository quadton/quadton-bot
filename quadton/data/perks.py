from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PerkDef:
    perk_id: str
    name: str
    description: str
    effect_type: str
    perk_class: str      # 'economic' or 'activity'
    strength: float      # e.g. 0.15 → +15%
    duration: int        # seconds
    cooldown: int        # seconds


PERKS: tuple[PerkDef, ...] = (
    PerkDef(
        "entrepreneur",
        "Entrepreneur",
        "+10% job pay for 1 hour.",
        effect_type="prosperity",
        perk_class="economic",
        strength=0.10,
        duration=3600,
        cooldown=24 * 3600,
    ),
    PerkDef(
        "gatherer",
        "Skilled Gatherer",
        "+15% gathering yield for 30 minutes.",
        effect_type="focus",
        perk_class="activity",
        strength=0.15,
        duration=1800,
        cooldown=12 * 3600,
    ),
    PerkDef(
        "scholar",
        "Scholar",
        "+25% XP from jobs for 1 hour.",
        effect_type="xp_boost",
        perk_class="activity",
        strength=0.25,
        duration=3600,
        cooldown=24 * 3600,
    ),
)


def by_id(perk_id: str) -> PerkDef | None:
    for p in PERKS:
        if p.perk_id == perk_id:
            return p
    return None
