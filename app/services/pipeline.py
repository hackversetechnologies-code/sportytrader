"""
PHASE 3 — Daily pipeline orchestrator. Wires together every phase from
fixture discovery through to the Telegram alert (FINAL BOT FLOW).

Fixtures are processed concurrently (bounded by PIPELINE_CONCURRENCY).
"""
import asyncio
from datetime import date, datetime, timedelta
import zoneinfo

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_football import ApiFootballClient
from app.database import get_insert_stmt
from app.logger import get_logger
from app.models import Prediction
from app.services.collection import collect_all_for_fixture
from app.services.consensus import evaluate_consensus
from app.services.dominance import compute_dominance
from app.services.features import run_feature_engineering
from app.services.filters import run_all_filters
from app.services.fixtures import discover_fixtures
from app.services.no3_engine import compute_no3_score
from app.services.ranking import assign_tiers, rank_matches
from app.services.safety import compute_safety_score
from app.services.scoring_types import MatchContext

logger = get_logger(__name__)

PIPELINE_CONCURRENCY = 2


async def _score_one(ctx: MatchContext) -> MatchContext:
    run_feature_engineering(ctx)
    run_all_filters(ctx)
    if ctx.rejected:
        return ctx
    compute_dominance(ctx)
    if ctx.dominance_score > 60:
        ctx.reject(f"Dominance too high ({ctx.dominance_score})")
        return ctx
    compute_no3_score(ctx)
    compute_safety_score(ctx)
    evaluate_consensus(ctx)
    return ctx


async def _process_fixture(client: ApiFootballClient, fixture, semaphore: asyncio.Semaphore) -> MatchContext:
    async with semaphore:
        data = await collect_all_for_fixture(client, fixture)
        ctx = MatchContext(
            fixture=fixture,
            home_stats=data["home_stats"],
            away_stats=data["away_stats"],
            h2h=data["h2h"],
            odds=data["odds"],
        )
        return await _score_one(ctx)


async def _persist_predictions(session: AsyncSession, tiers: dict, target_day: date) -> None:
    """
    Reset old predictions for target_day using exact target_date string to prevent cross-day mixing.
    """
    target_date_str = target_day.isoformat()
    await session.execute(
        delete(Prediction).where(Prediction.target_date == target_date_str)
    )

    top6 = tiers.get("TOP6", [])
    top3 = tiers.get("TOP3", [])
    top2 = tiers.get("TOP2", [])

    top3_ids = {c.fixture.fixture_id for c in top3}
    top2_ids = {c.fixture.fixture_id for c in top2}

    for rank, ctx in enumerate(top6, start=1):
        fixture = ctx.fixture
        fid = fixture.fixture_id

        if fid in top2_ids:
            assigned_tier = "TOP2"
        elif fid in top3_ids:
            assigned_tier = "TOP3"
        else:
            assigned_tier = "TOP6"

        stmt = get_insert_stmt(Prediction).values(
            fixture_id=fid,
            home_team=fixture.home_team,
            away_team=fixture.away_team,
            league_name=fixture.league_name,
            kickoff=fixture.date,
            target_date=target_date_str,
            no3_score=ctx.no3_score,
            dominance_score=ctx.dominance_score,
            safety_score=ctx.safety_score,
            passed_consensus=ctx.passed_consensus,
            consensus_votes=ctx.consensus_votes,
            rank=rank,
            tier=assigned_tier,
            rejected_reason=ctx.rejected_reason,
            result="PENDING",
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["fixture_id"],
            set_={
                "target_date": stmt.excluded.target_date,
                "no3_score": stmt.excluded.no3_score,
                "dominance_score": stmt.excluded.dominance_score,
                "safety_score": stmt.excluded.safety_score,
                "passed_consensus": stmt.excluded.passed_consensus,
                "consensus_votes": stmt.excluded.consensus_votes,
                "rank": stmt.excluded.rank,
                "tier": stmt.excluded.tier,
            },
        )
        await session.execute(stmt)
    await session.commit()


async def run_daily_pipeline(
    session: AsyncSession, client: ApiFootballClient, target_day: date | None = None, timezone: str = "Africa/Lagos"
) -> dict:
    if target_day is None:
        try:
            tz = zoneinfo.ZoneInfo(timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("Africa/Lagos")
        target_day = datetime.now(tz).date() + timedelta(days=1)
    logger.info("Running NO-3 daily pipeline for %s (full competition scan)", target_day)

    fixtures = await discover_fixtures(session, client, target_day, timezone)
    if not fixtures:
        logger.info("No playable fixtures found for %s", target_day)
        return {"tiers": {}, "total": 0}

    semaphore = asyncio.Semaphore(PIPELINE_CONCURRENCY)
    contexts: list[MatchContext] = await asyncio.gather(
        *(_process_fixture(client, fixture, semaphore) for fixture in fixtures)
    )

    ranked = rank_matches(contexts)
    tiers = assign_tiers(ranked)
    await _persist_predictions(session, tiers, target_day)

    logger.info(
        "Pipeline complete: %s fixtures scanned across all competitions, %s cleared the ELITE gate",
        len(contexts), len(ranked),
    )
    return {"tiers": tiers, "total": len(contexts), "passed": len(ranked)}
