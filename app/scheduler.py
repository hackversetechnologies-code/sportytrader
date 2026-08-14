"""
PHASE 3 + PHASE 17 — APScheduler jobs:
  - Daily pipeline at 10 PM Nigerian time (22:00 WAT = 21:00 UTC)
  - Pre-kickoff recheck on a short interval

Timezone note:
  APScheduler 3.x is built on pytz, NOT zoneinfo.  Passing a
  zoneinfo.ZoneInfo object can cause silent drift on some platforms.
  To avoid all ambiguity we schedule in UTC: 22:00 WAT = 21:00 UTC.
  The pipeline itself still receives Africa/Lagos for date calculations.
"""
from datetime import timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.api_football import ApiFootballClient
from app.bot.bot import send_alert
from app.bot.formatting import main_menu_keyboard, format_tier_message
from app.config import get_settings
from app.database import async_session
from app.logger import get_logger
from app.models import Prediction
from app.services.pipeline import run_daily_pipeline
from app.services.recheck import run_recheck_job

settings = get_settings()
logger = get_logger(__name__)

NIGERIA_TZ = ZoneInfo("Africa/Lagos")

# 22:00 WAT (Nigeria, UTC+1) = 21:00 UTC — hardcoded to avoid pytz/zoneinfo drift
_DAILY_RUN_HOUR_UTC = 21
_DAILY_RUN_MINUTE_UTC = 0


async def _query_predictions_for_broadcast(target_day_str: str, tier: str) -> list[Prediction]:
    """
    Query the DB for persisted Prediction objects for a given tier and target_date.
    TOP6 → all (max 6)
    TOP3 → TOP2 + TOP3 (max 3)
    TOP2 → TOP2 only (max 2)
    """
    tier_map = {
        "TOP6": (["TOP2", "TOP3", "TOP6"], 6),
        "TOP3": (["TOP2", "TOP3"],         3),
        "TOP2": (["TOP2"],                 2),
    }
    allowed, limit = tier_map.get(tier, (["TOP2", "TOP3", "TOP6"], 6))

    async with async_session() as session:
        result = await session.execute(
            select(Prediction)
            .where(
                Prediction.target_date == target_day_str,
                Prediction.tier.in_(allowed),
                Prediction.passed_consensus.is_(True),
                Prediction.removed_at_recheck.is_(False),
            )
            .order_by(Prediction.rank.asc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def daily_pipeline_job(client: ApiFootballClient) -> None:
    """
    Run daily scan for tomorrow's fixtures (Nigeria time) and broadcast
    TOP6 → TOP3 → TOP2 to all connected users.

    After the pipeline persists predictions to DB, we QUERY the DB to get
    proper Prediction objects (not MatchContext) for formatting.
    """
    try:
        from datetime import datetime
        target_day = datetime.now(NIGERIA_TZ).date() + timedelta(days=1)
        target_day_str = target_day.isoformat()
        logger.info(
            "Scheduled daily pipeline firing — target_day=%s (Nigeria time=%s)",
            target_day_str,
            datetime.now(NIGERIA_TZ).strftime("%Y-%m-%d %H:%M WAT"),
        )

        # Step 1: Run the pipeline (scores, ranks, persists to DB)
        async with async_session() as session:
            result = await run_daily_pipeline(
                session, client,
                target_day=target_day,
                timezone="Africa/Lagos",
            )
        passed = result.get("passed", 0)
        total  = result.get("total", 0)
        logger.info("Pipeline done — %s scanned, %s cleared gate", total, passed)

        # Step 2: Query DB for actual Prediction objects (correct types for formatting)
        top6_preds = await _query_predictions_for_broadcast(target_day_str, "TOP6")
        top3_preds = await _query_predictions_for_broadcast(target_day_str, "TOP3")
        top2_preds = await _query_predictions_for_broadcast(target_day_str, "TOP2")

        if not top6_preds:
            await send_alert(
                f"⚽ <b>NO-3 ENGINE</b>\n\n"
                f"⏳ No fixtures cleared the 85% NO-3 / 100% Safety gate "
                f"for {target_day.strftime('%A, %d %B %Y')}.",
                reply_markup=main_menu_keyboard(),
            )
            return

        # Step 3: Broadcast — TOP6 first, then TOP3, then TOP2
        await send_alert(
            format_tier_message("TOP6", top6_preds, target_day=target_day),
            reply_markup=main_menu_keyboard(),
        )
        if top3_preds:
            await send_alert(
                format_tier_message("TOP3", top3_preds, target_day=target_day),
                reply_markup=main_menu_keyboard(),
            )
        if top2_preds:
            await send_alert(
                format_tier_message("TOP2", top2_preds, target_day=target_day),
                reply_markup=main_menu_keyboard(),
            )
        logger.info("Daily broadcast complete — TOP6=%s TOP3=%s TOP2=%s",
                    len(top6_preds), len(top3_preds), len(top2_preds))

    except Exception as e:
        logger.error("Error running daily pipeline job: %s", e, exc_info=True)


async def recheck_job(client: ApiFootballClient) -> None:
    async with async_session() as session:
        survivors = await run_recheck_job(session, client, settings.recheck_window_minutes)
        logger.info("Recheck pass complete, %s predictions still standing", len(survivors))


def build_scheduler(client: ApiFootballClient) -> AsyncIOScheduler:
    # Use UTC scheduler — no pytz/zoneinfo ambiguity
    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        daily_pipeline_job,
        trigger=CronTrigger(
            hour=_DAILY_RUN_HOUR_UTC,
            minute=_DAILY_RUN_MINUTE_UTC,
            timezone="UTC",
        ),
        args=[client],
        id="daily_pipeline",
        replace_existing=True,
        misfire_grace_time=1800,  # allow up to 30 minutes late (e.g. if bot restarts)
    )

    scheduler.add_job(
        recheck_job,
        trigger=IntervalTrigger(minutes=settings.recheck_interval_minutes),
        args=[client],
        id="prekickoff_recheck",
        replace_existing=True,
        misfire_grace_time=300,
    )

    logger.info(
        "Scheduler built — daily job at %02d:%02d UTC (= 22:00 Nigeria WAT)",
        _DAILY_RUN_HOUR_UTC, _DAILY_RUN_MINUTE_UTC,
    )
    return scheduler
