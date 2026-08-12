"""
PHASE 18 — Learning system.

Settles predictions once results are known and logs them to MatchResult.
Provides simple aggregate stats (league win rates, failure causes) once
enough matches have accumulated.
"""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logger import get_logger
from app.models import MatchResult, Prediction

logger = get_logger(__name__)

MILESTONES = (100, 500, 1000)


async def settle_prediction(
    session: AsyncSession, prediction: Prediction, final_home_goals: int, final_away_goals: int
) -> MatchResult:
    diff = abs(final_home_goals - final_away_goals)
    failed = diff >= 3
    result = "FAILED" if failed else "WON"
    reason = None
    if failed:
        reason = "Blowout margin (3+) occurred despite pick"

    prediction.result = result
    prediction.final_score = f"{final_home_goals}-{final_away_goals}"
    prediction.updated_at = datetime.utcnow()

    log_row = MatchResult(
        fixture_id=prediction.fixture_id,
        match_label=f"{prediction.home_team} vs {prediction.away_team}",
        league_name=prediction.league_name,
        prediction="NO-3",
        result=result,
        final_score=prediction.final_score,
        reason=reason,
        no3_score=prediction.no3_score,
        safety_score=prediction.safety_score,
    )
    session.add(log_row)
    await session.commit()

    total = await session.scalar(select(func.count()).select_from(MatchResult))
    if total in MILESTONES:
        logger.info("Learning system milestone reached: %s settled matches", total)

    return log_row


async def get_league_win_rates(session: AsyncSession) -> list[dict]:
    # Plain aggregation in Python keeps this portable across DB backends.
    rows = (await session.execute(select(MatchResult.league_name, MatchResult.result))).all()
    stats: dict[str, dict[str, int]] = {}
    for league_name, res in rows:
        s = stats.setdefault(league_name, {"total": 0, "wins": 0})
        s["total"] += 1
        if res == "WON":
            s["wins"] += 1
    return [
        {"league": league, "total": s["total"], "win_rate": round(s["wins"] / s["total"] * 100, 1)}
        for league, s in stats.items()
    ]


async def get_failure_causes(session: AsyncSession) -> list[dict]:
    rows = (
        await session.execute(
            select(MatchResult.reason, func.count()).where(MatchResult.result == "FAILED").group_by(MatchResult.reason)
        )
    ).all()
    return [{"reason": reason or "unspecified", "count": count} for reason, count in rows]
