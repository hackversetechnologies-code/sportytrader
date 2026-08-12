"""
Entrypoint. Runs:
  - FastAPI app (health check + a couple of debug endpoints)
  - Aiogram bot polling (background task)
  - APScheduler (daily pipeline + pre-kickoff recheck)

Run with: python -m app.main   (or via the Dockerfile CMD)
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import date, timedelta

import redis.asyncio as aioredis
import uvicorn
from fastapi import FastAPI
from sqlalchemy import select

from app.api_football import ApiFootballClient
from app.bot.bot import bot, dp
from app.bot.handlers import router as bot_router
from app.config import get_settings
from app.database import async_session, init_db
from app.logger import get_logger
from app.models import Prediction
from app.scheduler import build_scheduler

settings = get_settings()
logger = get_logger(__name__)

dp.include_router(bot_router)

_background_tasks: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NO-3 bot system...")
    await init_db()

    redis_client = None
    if settings.redis_url:
        try:
            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            await asyncio.wait_for(r.ping(), timeout=2.0)
            redis_client = r
            logger.info("Connected to Redis at %s", settings.redis_url)
        except Exception as err:
            logger.warning("Redis not available (%s). Continuing without Redis.", err)
            redis_client = None

    api_client = ApiFootballClient(redis_client=redis_client)

    scheduler = build_scheduler(api_client)
    scheduler.start()

    polling_task = asyncio.create_task(dp.start_polling(bot, api_client=api_client))
    _background_tasks.append(polling_task)

    app.state.api_client = api_client
    app.state.redis = redis_client
    app.state.scheduler = scheduler

    logger.info("NO-3 bot system is live.")
    yield

    logger.info("Shutting down...")
    scheduler.shutdown(wait=False)
    polling_task.cancel()
    await api_client.close()
    if redis_client:
        await redis_client.close()


app = FastAPI(title="NO-3 Engine", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/predictions/tomorrow")
async def predictions_tomorrow():
    target = date.today() + timedelta(days=1)
    start = target
    end = target + timedelta(days=1)
    async with async_session() as session:
        result = await session.execute(
            select(Prediction).where(
                Prediction.kickoff >= start, Prediction.kickoff < end, Prediction.passed_consensus.is_(True)
            ).order_by(Prediction.no3_score.desc())
        )
        rows = result.scalars().all()
        return [
            {
                "fixture_id": r.fixture_id,
                "match": f"{r.home_team} vs {r.away_team}",
                "league": r.league_name,
                "kickoff": r.kickoff.isoformat(),
                "no3_score": r.no3_score,
                "dominance_score": r.dominance_score,
                "safety_score": r.safety_score,
                "tier": r.tier,
            }
            for r in rows
        ]


@app.post("/pipeline/run")
async def trigger_pipeline():
    """Manual trigger, useful for testing without waiting for the cron job."""
    from app.services.pipeline import run_daily_pipeline

    async with async_session() as session:
        target = date.today() + timedelta(days=1)
        result = await run_daily_pipeline(session, app.state.api_client, target_day=target, timezone=settings.timezone)
        return {"total_scanned": result["total"], "passed_consensus": result.get("passed", 0)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=settings.log_level.lower())
