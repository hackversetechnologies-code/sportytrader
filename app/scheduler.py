"""
PHASE 3 + PHASE 17 — APScheduler jobs:
  - Daily pipeline at midnight (configurable hour/minute)
  - Pre-kickoff recheck on a short interval, scanning for fixtures inside
    the recheck window
"""
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.api_football import ApiFootballClient
from app.bot.bot import send_alert
from app.config import get_settings
from app.database import async_session
from app.logger import get_logger
from app.services.pipeline import run_daily_pipeline
from app.services.recheck import run_recheck_job

settings = get_settings()
logger = get_logger(__name__)


async def daily_pipeline_job(client: ApiFootballClient) -> None:
    async with async_session() as session:
        target_day = date.today() + timedelta(days=1)
        result = await run_daily_pipeline(session, client, target_day=target_day, timezone=settings.timezone)
        tiers = result.get("tiers", {})
        top6 = tiers.get("TOP6", [])
        top3 = tiers.get("TOP3", [])
        top2 = tiers.get("TOP2", [])

        from app.bot.formatting import main_menu_keyboard, format_tier_message

        if not top6:
            await send_alert(
                "⚽ <b>NO-3 ENGINE</b>\n\n"
                "⏳ No fixtures cleared the 85% NO-3 / 100% Safety gate for tomorrow's slate.",
                reply_markup=main_menu_keyboard(),
            )
            return

        await send_alert(format_tier_message("TOP6", top6), reply_markup=main_menu_keyboard())
        if top3:
            await send_alert(format_tier_message("TOP3", top3), reply_markup=main_menu_keyboard())
        if top2:
            await send_alert(format_tier_message("TOP2", top2), reply_markup=main_menu_keyboard())


async def recheck_job(client: ApiFootballClient) -> None:
    async with async_session() as session:
        survivors = await run_recheck_job(session, client, settings.recheck_window_minutes)
        logger.info("Recheck pass complete, %s predictions still standing", len(survivors))


def build_scheduler(client: ApiFootballClient) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)

    scheduler.add_job(
        daily_pipeline_job,
        trigger=CronTrigger(hour=settings.daily_run_hour, minute=settings.daily_run_minute),
        args=[client],
        id="daily_pipeline",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        recheck_job,
        trigger=IntervalTrigger(minutes=settings.recheck_interval_minutes),
        args=[client],
        id="prekickoff_recheck",
        replace_existing=True,
        misfire_grace_time=300,
    )

    return scheduler
