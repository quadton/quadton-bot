from __future__ import annotations

# Rank score = net_worth + achievements*500 + total_job_levels*250.
# Rank thresholds are cumulative; the top rank is unbounded.

RANKS: tuple[tuple[str, int], ...] = (
    ("Bronze", 0),
    ("Silver", 5_000),
    ("Gold", 25_000),
    ("Platinum", 100_000),
    ("Diamond", 500_000),
    ("Emerald", 2_000_000),
    ("Champion", 10_000_000),
)


def rank_for(score: int) -> dict:
    idx = 0
    for i, (_, threshold) in enumerate(RANKS):
        if score >= threshold:
            idx = i
    name = RANKS[idx][0]
    if idx == len(RANKS) - 1:
        return {
            "rank": name,
            "next": None,
            "score_into_rank": score - RANKS[idx][1],
            "points_to_next": 0,
        }
    next_name, next_threshold = RANKS[idx + 1]
    return {
        "rank": name,
        "next": next_name,
        "score_into_rank": score - RANKS[idx][1],
        "points_to_next": next_threshold - score,
    }


def score(net_worth: int, achievements: int, total_job_levels: int) -> int:
    return net_worth + achievements * 500 + total_job_levels * 250
