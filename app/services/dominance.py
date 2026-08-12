"""
PHASE 11 — Dominance Engine.

    40% Strength Gap
    20% Form Gap
    20% H2H Gap
    10% Odds Gap
    10% Home Advantage

Lower dominance score = the two teams are closer / more balanced, which is
what NO-3 wants (rule bands: 0-20 Excellent, 21-35 Good, 36-50 Risky, 51+ Reject).
"""
from app.services.scoring_types import MatchContext

WEIGHTS = {
    "strength": 0.40,
    "form": 0.20,
    "h2h": 0.20,
    "odds": 0.10,
    "home_advantage": 0.10,
}


def _form_points(form: str | None) -> int:
    if not form:
        return 0
    mapping = {"W": 3, "D": 1, "L": 0}
    return sum(mapping.get(c, 0) for c in form)


def _form_gap(ctx: MatchContext) -> float:
    home, away = ctx.home_stats, ctx.away_stats
    if not home or not away:
        return 0.0
    home_pts = _form_points(home.form)
    away_pts = _form_points(away.form)
    max_pts = 15  # 5 games * 3 pts
    return min(100.0, abs(home_pts - away_pts) / max_pts * 100.0)


def _h2h_gap(ctx: MatchContext) -> float:
    if not ctx.h2h:
        return 0.0
    home_wins = sum(1 for r in ctx.h2h if r.home_goals > r.away_goals)
    away_wins = sum(1 for r in ctx.h2h if r.away_goals > r.home_goals)
    total = len(ctx.h2h)
    return min(100.0, abs(home_wins - away_wins) / total * 100.0) if total else 0.0


def _odds_gap(ctx: MatchContext) -> float:
    """Uses the 1X2 market implied-probability spread as a proxy for perceived gap."""
    if not ctx.odds:
        return 0.0
    try:
        bookmakers = ctx.odds[0].get("bookmakers", [])
        if not bookmakers:
            return 0.0
        bets = bookmakers[0].get("bets", [])
        match_winner = next((b for b in bets if b.get("name") == "Match Winner"), None)
        if not match_winner:
            return 0.0
        values = {v["value"]: float(v["odd"]) for v in match_winner.get("values", [])}
        home_odd, away_odd = values.get("Home"), values.get("Away")
        if not home_odd or not away_odd:
            return 0.0
        home_prob = 1 / home_odd
        away_prob = 1 / away_odd
        total = home_prob + away_prob
        if total == 0:
            return 0.0
        return min(100.0, abs(home_prob - away_prob) / total * 100.0)
    except (KeyError, ValueError, ZeroDivisionError, TypeError):
        return 0.0


def _home_advantage(ctx: MatchContext) -> float:
    """0-100, higher = home side has a stronger home-venue edge (adds to dominance)."""
    home = ctx.home_stats
    if not home:
        return 0.0
    played = home.home_wins + home.home_draws + home.home_losses
    if not played:
        return 0.0
    win_rate = home.home_wins / played
    return round(win_rate * 100.0, 2)


def compute_dominance(ctx: MatchContext) -> float:
    score = (
        ctx.strength_gap * WEIGHTS["strength"]
        + _form_gap(ctx) * WEIGHTS["form"]
        + _h2h_gap(ctx) * WEIGHTS["h2h"]
        + _odds_gap(ctx) * WEIGHTS["odds"]
        + _home_advantage(ctx) * WEIGHTS["home_advantage"]
    )
    ctx.dominance_score = round(min(100.0, score), 2)
    return ctx.dominance_score


def dominance_band(score: float) -> str:
    if score <= 20:
        return "Excellent"
    if score <= 35:
        return "Good"
    if score <= 50:
        return "Risky"
    return "Reject"
