"""
PHASE 15 — Ranking Engine (updated funnel).

Only matches that already cleared the ELITE hard gate (NO-3 >= 85 AND
Safety == 100) ever reach this stage — see consensus.py. Everything else
was dropped before ranking runs, so there is no "reject at ranking time"
step anymore.

Funnel:
    All ELITE matches
        -> TOP6   (first 6, ranked by NO-3 score — highest confidence first)
        -> TOP3   (best 3 of those 6, re-sorted by dominance — lowest
                   dominance = closest/safest matchup — then NO-3 as tiebreak)
        -> TOP2   (the safest 2 of those 3 — dominance ascending is the
                   primary sort since every match here already has NO-3 >= 85
                   and Safety == 100, so dominance is what actually
                   separates "safe" from "safest")
"""
from app.services.scoring_types import MatchContext

TIER_SIZES = [
    ("TOP6", 6),
    ("TOP3", 3),
    ("TOP2", 2),
]


def rank_matches(contexts: list[MatchContext]) -> list[MatchContext]:
    """Only ELITE-gated matches (passed_consensus, not rejected) are eligible at all."""
    eligible = [c for c in contexts if c.passed_consensus and not c.rejected]
    # Highest NO-3 confidence first; dominance as tiebreak (lower = safer).
    eligible.sort(key=lambda c: (c.no3_score, -c.dominance_score), reverse=True)
    return eligible


def assign_tiers(ranked: list[MatchContext]) -> dict[str, list[MatchContext]]:
    """
    Builds the funnel. Each successive tier is a re-sorted subset of the
    previous one, not just a shorter slice of the same order — TOP3 and
    TOP2 specifically optimize for safety (lowest dominance) once the
    NO-3/Safety hard gate has already been satisfied by everyone present.
    """
    tiers: dict[str, list[MatchContext]] = {}

    top6 = ranked[:6]
    tiers["TOP6"] = top6

    top3_pool = sorted(top6, key=lambda c: (c.dominance_score, -c.no3_score))
    top3 = top3_pool[:3]
    tiers["TOP3"] = top3

    top2_pool = sorted(top3, key=lambda c: (c.dominance_score, -c.safety_score, -c.no3_score))
    top2 = top2_pool[:2]
    tiers["TOP2"] = top2

    return tiers
