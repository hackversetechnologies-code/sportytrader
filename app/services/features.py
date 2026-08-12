"""
PHASE 7 — Feature engineering.

Turns raw team-statistics rows into normalized 0-100 gap/balance scores.
All scores are "gap" style: higher = bigger mismatch between the two teams
(used later by filters that want blowouts flagged), except home_away_balance
which is a straight 0-100 reliability score.
"""
from app.models import TeamStatistics
from app.services.scoring_types import MatchContext


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _ppg(stats: TeamStatistics) -> float:
    if not stats or not stats.matches_played:
        return 0.0
    points = stats.wins * 3 + stats.draws
    return points / stats.matches_played


def _goals_per_match(stats: TeamStatistics, conceded: bool = False) -> float:
    if not stats or not stats.matches_played:
        return 0.0
    total = stats.goals_conceded if conceded else stats.goals_scored
    return total / stats.matches_played


def compute_strength_gap(ctx: MatchContext) -> float:
    """PPG difference + clean-sheet-rate difference, scaled to 0-100."""
    home, away = ctx.home_stats, ctx.away_stats
    if not home or not away:
        return 0.0
    ppg_diff = abs(_ppg(home) - _ppg(away))  # 0-3 range
    score = min(100.0, (ppg_diff / 3.0) * 100.0)
    ctx.strength_gap = round(score, 2)
    return ctx.strength_gap


def compute_attack_gap(ctx: MatchContext) -> float:
    home, away = ctx.home_stats, ctx.away_stats
    if not home or not away:
        return 0.0
    home_attack = _goals_per_match(home)
    away_attack = _goals_per_match(away)
    diff = abs(home_attack - away_attack)  # typically 0-3
    score = min(100.0, (diff / 3.0) * 100.0)
    ctx.attack_gap = round(score, 2)
    return ctx.attack_gap


def compute_defense_gap(ctx: MatchContext) -> float:
    home, away = ctx.home_stats, ctx.away_stats
    if not home or not away:
        return 0.0
    home_def = _goals_per_match(home, conceded=True)
    away_def = _goals_per_match(away, conceded=True)
    diff = abs(home_def - away_def)
    score = min(100.0, (diff / 3.0) * 100.0)
    ctx.defense_gap = round(score, 2)
    return ctx.defense_gap


def compute_home_away_balance(ctx: MatchContext) -> float:
    """How reliable each side is in its own venue — higher = more balanced/predictable."""
    home, away = ctx.home_stats, ctx.away_stats
    if not home or not away:
        return 0.0
    home_played = home.home_wins + home.home_draws + home.home_losses
    away_played = away.away_wins + away.away_draws + away.away_losses
    home_win_rate = _safe_div(home.home_wins, home_played)
    away_win_rate = _safe_div(away.away_wins, away_played)
    balance = 100.0 - (abs(home_win_rate - away_win_rate) * 100.0)
    ctx.home_away_balance = round(max(0.0, balance), 2)
    return ctx.home_away_balance


def run_feature_engineering(ctx: MatchContext) -> MatchContext:
    compute_strength_gap(ctx)
    compute_attack_gap(ctx)
    compute_defense_gap(ctx)
    compute_home_away_balance(ctx)
    return ctx
