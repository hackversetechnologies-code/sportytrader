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


def key_player_availability_filter(ctx: MatchContext) -> None:
    """
    Mandatory Rule 1: Key Player Availability Check.
    If key/main players from either team are benched, omitted from starting XI,
    or reported injured/suspended, immediately disqualify the match.
    """
    if ctx.injuries:
        missing_key = [
            inj for inj in ctx.injuries
            if (inj.get("player", {}).get("type") or "").lower() in ("missing fixture", "suspended", "doubtful", "benched")
        ]
        if len(missing_key) >= 1:
            player_names = ", ".join(i.get("player", {}).get("name", "Unknown") for i in missing_key[:3])
            ctx.reject(f"Key player omitted/unavailable: {player_names}")
            return

    if ctx.lineups:
        for team_lineup in ctx.lineups:
            substitutes = team_lineup.get("substitutes", [])
            benched_stars = [
                sub.get("player", {}).get("name")
                for sub in substitutes
                if sub.get("player", {}).get("rating") and float(sub.get("player", {}).get("rating") or 0) >= 7.5
            ]
            if benched_stars:
                ctx.reject(f"Key player benched in starting XI: {', '.join(benched_stars[:2])}")
                return


def goalkeeper_parity_filter(ctx: MatchContext) -> None:
    """
    Mandatory Rule 2: Goalkeeper Parity & Condition Check.
    Compare starting goalkeepers for both teams:
      - Pass: Both goalkeepers have comparable average ratings and are fully fit.
      - Disqualify: Disqualify if either GK is injured, returning from injury/not at peak form,
        or if there is a significant skill/rating disparity.
    """
    if ctx.injuries:
        gk_injuries = [
            inj for inj in ctx.injuries
            if "goalkeeper" in (inj.get("player", {}).get("position") or "").lower()
            or (inj.get("player", {}).get("pos") or "").upper() == "G"
        ]
        if gk_injuries:
            gk_names = ", ".join(i.get("player", {}).get("name", "GK") for i in gk_injuries)
            ctx.reject(f"Starting goalkeeper injured/unfit: {gk_names}")
            return

    if ctx.lineups and len(ctx.lineups) == 2:
        gk_ratings = []
        for team_lineup in ctx.lineups:
            start_xi = team_lineup.get("startXI", [])
            gks = [p for p in start_xi if (p.get("player", {}).get("pos") or "").upper() == "G"]
            if gks:
                rating = float(gks[0].get("player", {}).get("rating") or 6.5)
                gk_ratings.append(rating)

        if len(gk_ratings) == 2:
            disparity = abs(gk_ratings[0] - gk_ratings[1])
            if disparity >= 1.2:
                ctx.reject(f"Goalkeeper rating disparity too large ({gk_ratings[0]:.1f} vs {gk_ratings[1]:.1f})")


def defensive_lineup_strength_filter(ctx: MatchContext) -> None:
    """
    Mandatory Rule 3: Defensive Lineup Strength Check.
    Evaluate the defensive line for both teams. Disqualify if either team
    displays a compromised, weak, or insufficient defensive setup.
    """
    if ctx.injuries:
        def_injuries = [
            inj for inj in ctx.injuries
            if "defender" in (inj.get("player", {}).get("position") or "").lower()
            or (inj.get("player", {}).get("pos") or "").upper() == "D"
        ]
        if len(def_injuries) >= 2:
            ctx.reject(f"Compromised defensive lineup: {len(def_injuries)} key defenders injured/absent")
            return

    home, away = ctx.home_stats, ctx.away_stats
    if home and away and home.matches_played and away.matches_played:
        home_conceded_per_game = home.goals_conceded / home.matches_played
        away_conceded_per_game = away.goals_conceded / away.matches_played

        if home_conceded_per_game >= 2.2 or away_conceded_per_game >= 2.2:
            ctx.reject(
                f"Weak defensive line: home concedes {home_conceded_per_game:.2f} gpg, "
                f"away concedes {away_conceded_per_game:.2f} gpg"
            )


def run_all_filters(ctx: MatchContext) -> MatchContext:
    for filt in (
        h2h_blowout_filter,
        goal_explosion_filter,
        early_goal_filter,
        key_player_availability_filter,
        goalkeeper_parity_filter,
        defensive_lineup_strength_filter,
    ):
        filt(ctx)
        if ctx.rejected:
            break
    return ctx
