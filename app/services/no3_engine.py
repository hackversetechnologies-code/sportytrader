"""
PHASE 12 — NO-3 Engine (main score).

    Strength Gap   25%
    Attack Gap     20%
    Defense Gap    20%
    Home/Away      10%
    Draw Rate       5%
    BTTS Rate       5%
    H2H Balance    10%
    Motivation      5%

NO-3 targets *closeness* (low blowout risk), so every sub-score here is
inverted where needed such that a HIGH final no3_score means "safe, unlikely
to produce a 3+ goal margin" — matching the PHASE 14 rule of NO3 >= 85 to pass.
"""
from app.services.scoring_types import MatchContext

WEIGHTS = {
    "strength": 0.25,
    "attack": 0.20,
    "defense": 0.20,
    "home_away": 0.10,
    "draw_rate": 0.05,
    "btts_rate": 0.05,
    "h2h_balance": 0.10,
    "motivation": 0.05,
}


def _draw_rate(ctx: MatchContext) -> float:
    home, away = ctx.home_stats, ctx.away_stats
    if not home or not away or not home.matches_played or not away.matches_played:
        return 0.0
    home_rate = home.draws / home.matches_played
    away_rate = away.draws / away.matches_played
    return round(((home_rate + away_rate) / 2) * 100.0, 2)


def _btts_rate(ctx: MatchContext) -> float:
    """Approximate BTTS rate from goals-scored/conceded per match (both > ~1 implies teams tend to score)."""
    home, away = ctx.home_stats, ctx.away_stats
    if not home or not away or not home.matches_played or not away.matches_played:
        return 0.0
    home_scores = home.goals_scored / home.matches_played >= 1.0
    away_scores = away.goals_scored / away.matches_played >= 1.0
    home_concedes = home.goals_conceded / home.matches_played >= 1.0
    away_concedes = away.goals_conceded / away.matches_played >= 1.0
    hits = sum([home_scores, away_scores, home_concedes, away_concedes])
    return round((hits / 4) * 100.0, 2)


def _h2h_balance(ctx: MatchContext) -> float:
    """Inverted h2h gap — high score = historically balanced fixture."""
    if not ctx.h2h:
        return 50.0  # neutral when no history
    home_wins = sum(1 for r in ctx.h2h if r.home_goals > r.away_goals)
    away_wins = sum(1 for r in ctx.h2h if r.away_goals > r.home_goals)
    draws = sum(1 for r in ctx.h2h if r.home_goals == r.away_goals)
    total = len(ctx.h2h)
    if total == 0:
        return 50.0
    imbalance = abs(home_wins - away_wins) / total
    return round((1 - imbalance) * 100.0, 2)


def _motivation(ctx: MatchContext) -> float:
    """
    Estimate how much both sides have to play for.
    Uses recent form as a proxy — teams in consistent form are more motivated.
    Returns 0-100; default 65 when no data.
    """
    home, away = ctx.home_stats, ctx.away_stats
    if not home or not away:
        return 65.0

    def form_score(form_str: str | None) -> float:
        """Convert 'WWDLW' style form into 0-100 motivation score."""
        if not form_str:
            return 65.0
        recent = form_str[-5:]  # last 5 matches
        pts = sum({"W": 3, "D": 1, "L": 0}.get(ch.upper(), 1) for ch in recent)
        return round((pts / 15.0) * 100.0, 2)

    home_score = form_score(home.form)
    away_score = form_score(away.form)
    # Both sides motivated = high score; only one side = moderate
    return round((home_score + away_score) / 2, 2)


def compute_no3_score(ctx: MatchContext) -> float:
    inv_strength = 100.0 - ctx.strength_gap
    inv_attack = 100.0 - ctx.attack_gap
    inv_defense = 100.0 - ctx.defense_gap
    home_away = ctx.home_away_balance

    score = (
        inv_strength * WEIGHTS["strength"]
        + inv_attack * WEIGHTS["attack"]
        + inv_defense * WEIGHTS["defense"]
        + home_away * WEIGHTS["home_away"]
        + _draw_rate(ctx) * WEIGHTS["draw_rate"]
        + _btts_rate(ctx) * WEIGHTS["btts_rate"]
        + _h2h_balance(ctx) * WEIGHTS["h2h_balance"]
        + _motivation(ctx) * WEIGHTS["motivation"]
    )
    ctx.no3_score = round(min(100.0, max(0.0, score)), 2)
    return ctx.no3_score
