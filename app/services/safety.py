"""
PHASE 13 — Safety Engine.

Starts at 100 and subtracts deductions for risk factors. Deduction sizes
are explicit constants so they're easy to retune once the learning system
(PHASE 18) has enough settled results to justify adjusting them.
"""
from app.services.scoring_types import MatchContext

DEDUCTIONS = {
    "heavy_favorite": 15,      # dominance_score > 50
    "h2h_blowout": 100,        # handled as a hard reject upstream, kept here for completeness
    "goal_explosion": 20,
    "high_cards_risk": 10,
    "odds_movement": 10,
    "motivation_spike": 5,
}


def compute_safety_score(ctx: MatchContext, odds_moved_sharply: bool = False, high_card_risk: bool = False) -> float:
    score = 100.0

    if ctx.dominance_score > 50:
        score -= DEDUCTIONS["heavy_favorite"]

    if ctx.early_goal_risk >= 61:
        score -= DEDUCTIONS["goal_explosion"]

    if high_card_risk:
        score -= DEDUCTIONS["high_cards_risk"]

    if odds_moved_sharply:
        score -= DEDUCTIONS["odds_movement"]

    ctx.safety_score = round(max(0.0, score), 2)
    return ctx.safety_score
