"""
PHASE 8, 9, 10 — Mandatory reject filters.

Each function mutates the MatchContext in place, calling ctx.reject(reason)
when a hard-reject condition fires. run_all_filters() short-circuits on the
first rejection (no point burning more logic once a match is out).
"""
from datetime import datetime, timedelta

from app.models import H2HRecord
from app.services.scoring_types import MatchContext


def _is_blowout(home_goals: int, away_goals: int) -> bool:
    diff = abs(home_goals - away_goals)
    loser_goals = min(home_goals, away_goals)
    # 3-0 / 4-0 / 5-0 style: 3+ goal margin with the loser on zero, or any 3+ margin
    return diff >= 3 and loser_goals == 0


def h2h_blowout_filter(ctx: MatchContext) -> None:
    """PHASE 8 — reject on recent blowout history."""
    last_five = ctx.h2h[:5]
    for record in last_five:
        if _is_blowout(record.home_goals, record.away_goals):
            ctx.reject(f"H2H blowout in last 5: {record.home_goals}-{record.away_goals}")
            return

    one_year_ago = datetime.utcnow() - timedelta(days=365)
    for record in ctx.h2h:
        if record.match_date and record.match_date.replace(tzinfo=None) < one_year_ago:
            continue
        diff = abs(record.home_goals - record.away_goals)
        if diff >= 3:
            ctx.reject(f"Same team won by 3+ within last 12 months ({record.home_goals}-{record.away_goals})")
            return


def goal_explosion_filter(ctx: MatchContext) -> None:
    """
    PHASE 9 — Reject if either team has been regularly involved in
    high-scoring matches (4+ goals) in recent form.

    Uses the TeamStatistics data already in ctx (goals scored/conceded
    per match) as a proxy.  A team is flagged as "explosive" if:
      - Their goals_scored per match >= 2.5  (high attacking output), OR
      - Their goals_conceded per match >= 2.5 (leaky defence)

    If BOTH teams are explosive (attacker + leaky defence pairing) the
    fixture is rejected as a goal-fest risk.  A single flagged team is
    not enough on its own — we need the matchup to be mutually explosive.

    For a fully precise implementation, replace this with a
    /fixtures?team={id}&last=5 call per team and count individual
    matches where total goals >= 4.
    """
    home, away = ctx.home_stats, ctx.away_stats
    if not home or not away:
        return  # no data — can't filter, give benefit of the doubt

    if not home.matches_played or not away.matches_played:
        return

    home_scored_rate = home.goals_scored / home.matches_played
    home_conceded_rate = home.goals_conceded / home.matches_played
    away_scored_rate = away.goals_scored / away.matches_played
    away_conceded_rate = away.goals_conceded / away.matches_played

    EXPLOSION_THRESHOLD = 2.5  # goals per match

    home_explosive = (
        home_scored_rate >= EXPLOSION_THRESHOLD
        or home_conceded_rate >= EXPLOSION_THRESHOLD
    )
    away_explosive = (
        away_scored_rate >= EXPLOSION_THRESHOLD
        or away_conceded_rate >= EXPLOSION_THRESHOLD
    )

    if home_explosive and away_explosive:
        ctx.reject(
            f"Goal-explosion risk: home scores/concedes "
            f"{home_scored_rate:.1f}/{home_conceded_rate:.1f} gpg, "
            f"away {away_scored_rate:.1f}/{away_conceded_rate:.1f} gpg"
        )


def early_goal_filter(ctx: MatchContext) -> None:
    """
    PHASE 10 — classify early-goal risk (0-30 Safe / 31-60 Medium / 61+ Reject)
    based on goal-minute events pulled from /fixtures/events for each team's
    recent matches (ctx.home_events / ctx.away_events, minute field).
    """
    events = ctx.home_events + ctx.away_events
    if not events:
        ctx.early_goal_risk = 0.0
        return

    early_goals = 0
    total_goals = 0
    for ev in events:
        if ev.get("type") != "Goal":
            continue
        total_goals += 1
        minute = (ev.get("time") or {}).get("elapsed")
        if minute is not None and minute <= 20:
            early_goals += 1

    risk = (early_goals / total_goals * 100.0) if total_goals else 0.0
    ctx.early_goal_risk = round(risk, 2)

    if risk >= 61:
        ctx.reject(f"Early goal risk too high ({risk:.0f}%)")


def run_all_filters(ctx: MatchContext) -> MatchContext:
    for filt in (h2h_blowout_filter, goal_explosion_filter, early_goal_filter):
        filt(ctx)
        if ctx.rejected:
            break
    return ctx
