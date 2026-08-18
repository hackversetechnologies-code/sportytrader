"""
PHASE 17 — Pre-kickoff recheck.

Runs on a schedule (see app/scheduler.py) and looks for surviving
predictions whose kickoff is within the recheck window. Pulls fresh
lineups, injuries and odds; recomputes dominance; drops the pick if
things have degraded.
"""
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_football import ApiFootballClient
from app.logger import get_logger
from app.models import Prediction
from app.services.dominance import compute_dominance, _odds_gap
from app.services.fixtures import HARD_REJECT_STATUSES, PLAYABLE_STATUS
from app.services.scoring_types import MatchContext
from app.services.collection import collect_team_statistics, collect_h2h

logger = get_logger(__name__)

DOMINANCE_INCREASE_THRESHOLD = 10.0  # points
ODDS_SHIFT_THRESHOLD = 20.0  # points of implied-probability gap movement


async def get_due_predictions(session: AsyncSession, window_minutes: int) -> list[Prediction]:
    now = datetime.utcnow()
    cutoff = now + timedelta(minutes=window_minutes)
    result = await session.execute(
        select(Prediction).where(
            Prediction.passed_consensus.is_(True),
            Prediction.removed_at_recheck.is_(False),
            Prediction.kickoff >= now,
            Prediction.kickoff <= cutoff,
        )
    )
    return list(result.scalars().all())


async def recheck_prediction(
    session: AsyncSession, client: ApiFootballClient, prediction: Prediction
) -> bool:
    """Returns True if the pick survives, False if it was removed."""

    # Status check first — if the match has been cancelled, postponed,
    # abandoned, etc. since it was scored, it's hard rejected immediately
    # and none of the other recheck logic even runs.
    fresh_fixture = await client.get_fixture_by_id(prediction.fixture_id)
    if fresh_fixture:
        status_short = fresh_fixture.get("fixture", {}).get("status", {}).get("short", PLAYABLE_STATUS)
        if status_short in HARD_REJECT_STATUSES:
            prediction.removed_at_recheck = True
            prediction.passed_consensus = False
            prediction.rejected_reason = f"Status changed to {status_short} ({HARD_REJECT_STATUSES[status_short]})"
            await session.commit()
            logger.info(
                "Hard rejected fixture %s at recheck: status changed to %s", prediction.fixture_id, status_short
            )
            return False

    injuries = await client.get_injuries(prediction.fixture_id)
    lineups = await client.get_lineups(prediction.fixture_id)
    fresh_odds = await client.get_odds(prediction.fixture_id)

    removed = False
    reason = None

    # Odds movement check
    old_gap_proxy = prediction.dominance_score
    try:
        bookmakers = fresh_odds[0].get("bookmakers", []) if fresh_odds else []
        bets = bookmakers[0].get("bets", []) if bookmakers else []
        match_winner = next((b for b in bets if b.get("name") == "Match Winner"), None)
        if match_winner:
            values = {v["value"]: float(v["odd"]) for v in match_winner.get("values", [])}
            home_odd, away_odd = values.get("Home"), values.get("Away")
            if home_odd and away_odd:
                home_prob, away_prob = 1 / home_odd, 1 / away_odd
                total = home_prob + away_prob
                new_gap = abs(home_prob - away_prob) / total * 100.0 if total else 0.0
                if new_gap - old_gap_proxy >= ODDS_SHIFT_THRESHOLD:
                    removed = True
                    reason = f"Sharp odds movement (gap moved to {new_gap:.0f})"
    except (KeyError, ValueError, ZeroDivisionError, TypeError, IndexError):
        pass

    # 3 Mandatory Match Selection Rules & Disqualification Criteria:
    # 1. Key Player Availability Check
    # 2. Goalkeeper Parity & Condition Check
    # 3. Defensive Lineup Strength Check
    if not removed:
        from app.services.filters import (
            key_player_availability_filter,
            goalkeeper_parity_filter,
            defensive_lineup_strength_filter,
        )
        ctx = MatchContext(
            fixture=None,
            home_stats=None,
            away_stats=None,
            h2h=[],
            odds=fresh_odds,
            injuries=injuries,
            lineups=lineups,
        )
        for filt in (key_player_availability_filter, goalkeeper_parity_filter, defensive_lineup_strength_filter):
            filt(ctx)
            if ctx.rejected:
                removed = True
                reason = ctx.rejected_reason
                break

    if removed:
        prediction.removed_at_recheck = True
        prediction.rejected_reason = reason
        prediction.passed_consensus = False
        await session.commit()
        logger.info("Removed fixture %s at recheck: %s", prediction.fixture_id, reason)
        return False

    return True


async def run_recheck_job(session: AsyncSession, client: ApiFootballClient, window_minutes: int) -> list[Prediction]:
    due = await get_due_predictions(session, window_minutes)
    survivors = []
    for pred in due:
        ok = await recheck_prediction(session, client, pred)
        if ok:
            survivors.append(pred)
    return survivors
