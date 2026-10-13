from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobDef:
    job_id: str
    name: str
    description: str
    base_pay: int
    cooldown: int  # seconds
    xp_per_work: int
    max_level: int = 50


JOBS: tuple[JobDef, ...] = (
    JobDef("delivery", "Delivery Worker", "Deliver packages.", 60, 600, 10),
    JobDef("miner", "Miner", "Extract ore.", 75, 900, 12),
    JobDef("fisher", "Fisher", "Catch fish.", 70, 800, 11),
    JobDef("mechanic", "Mechanic", "Fix machines.", 90, 1100, 14),
    JobDef("chef", "Chef", "Cook meals.", 100, 1200, 15),
    JobDef("engineer", "Engineer", "Design systems.", 130, 1500, 18),
    JobDef("merchant", "Merchant", "Trade goods.", 150, 1800, 20),
    JobDef("explorer", "Explorer", "Chart territory.", 160, 2000, 22),
    JobDef("manager", "Business Manager", "Run a company.", 200, 2400, 25),
    JobDef("analyst", "Financial Analyst", "Analyze markets.", 240, 2700, 30),
)


def by_id(job_id: str) -> JobDef | None:
    for j in JOBS:
        if j.job_id == job_id:
            return j
    return None


def xp_needed(level: int) -> int:
    return 100 + (level - 1) * 50


def pay_for(job: JobDef, level: int) -> int:
    # 5% raise per level over base.
    return int(job.base_pay * (1 + 0.05 * (level - 1)))
