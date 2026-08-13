"""
Telegram bot command handlers with inline keyboards.

Flow:
  📅 Today button    → scan API for today (Nigeria GMT+1) + show ELITE picks
  🌅 Tomorrow button → scan API for tomorrow (Nigeria GMT+1) + show ELITE picks
  🏆 Top 6           → show top 6 from last scan (DB)      — up to 6 picks
  🥇 Top 3           → show top 3 sieved from top 6 (DB)  — up to 3 picks
  🔒 Top 2           → show top 2 sieved from top 3 (DB)  — up to 2 picks

All results are posted as NEW messages — existing messages are never deleted.
All date calculations use Nigeria time (Africa/Lagos, GMT+1).
"""
import html
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.api_football import ApiFootballClient
from app.bot.bot import register_user
from app.bot.formatting import (
    back_keyboard,
    format_tier_message,
    main_menu_keyboard,
    HEADER,
)
from app.config import get_settings
from app.database import async_session
from app.models import Prediction
from app.services.pipeline import run_daily_pipeline

router = Router()
settings = get_settings()

PARSE_MODE = "HTML"

# ── Nigerian timezone (GMT+1) ──────────────────────────────────
NIGERIA_TZ = ZoneInfo("Africa/Lagos")


def nigeria_today() -> date:
    """Return the current date in Nigerian time (Africa/Lagos, GMT+1)."""
    return datetime.now(NIGERIA_TZ).date()


WELCOME = (
    f"{HEADER}\n\n"
    "🎯 <b>Automated match screening</b>\n\n"
    "Only fixtures scoring <b>NO-3 ≥ 85</b> <i>and</i> <b>Safety = 100</b> make the list — "
    "everything else is dropped.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "📅 <b>Today</b> — Scan &amp; show today's ELITE picks\n"
    "🌅 <b>Tomorrow</b> — Scan &amp; show tomorrow's ELITE picks\n"
    "🏆 <b>Top 6</b> — Best 6 picks from last scan\n"
    "🥇 <b>Top 3</b> — Best 3 picks sieved from Top 6\n"
    "🔒 <b>Top 2</b> — Safest 2 locks sieved from Top 3\n\n"
    "Or use commands: <code>/today</code> <code>/tomorrow</code> "
    "<code>/top6</code> <code>/top3</code> <code>/top2</code> <code>/run</code>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🔔 <i>Auto-scan + broadcast runs every night at 10:00 PM Nigerian time.</i>\n"
)


# ── Helpers ────────────────────────────────────────────────────

async def _reg(obj) -> None:
    try:
        if isinstance(obj, Message):
            chat_id, user = obj.chat.id, obj.from_user
        else:
            chat_id, user = obj.message.chat.id, obj.from_user
        if user:
            await register_user(chat_id, user.username, user.first_name)
    except Exception:
        pass


async def _predictions_for_day(target_day: date) -> list[Prediction]:
    """Fetch all TOP6-gated predictions for target_day ordered by rank."""
    target_str = target_day.isoformat()
    async with async_session() as session:
        result = await session.execute(
            select(Prediction)
            .where(
                Prediction.target_date == target_str,
                Prediction.tier.in_(["TOP2", "TOP3", "TOP6"]),
                Prediction.passed_consensus.is_(True),
                Prediction.removed_at_recheck.is_(False),
            )
            .order_by(Prediction.rank.asc())
            .limit(6)
        )
        return list(result.scalars().all())


# ── Strict funnel queries ─────────────────────────────────────
# TOP6: queries tier IN ('TOP2','TOP3','TOP6'), limits to 6   (all elite picks)
# TOP3: queries tier IN ('TOP2','TOP3'),        limits to 3   (sieved from TOP6)
# TOP2: queries tier IN ('TOP2'),               limits to 2   (sieved from TOP3)

_TIER_FILTERS = {
    "TOP6": (["TOP2", "TOP3", "TOP6"], 6),
    "TOP3": (["TOP2", "TOP3"],         3),
    "TOP2": (["TOP2"],                 2),
}


async def _predictions_by_tier(tier: str) -> list[Prediction]:
    """
    Return predictions for the requested tier from the most recent scan day
    (prefer tomorrow, then today — both in Nigerian time).

    Strict funnel:
      TOP6  ← all ELITE picks           (max 6)
      TOP3  ← sieved from TOP6          (max 3, subset of TOP6)
      TOP2  ← sieved from TOP3          (max 2, subset of TOP3)
    """
    allowed_tiers, limit = _TIER_FILTERS.get(tier, ([tier], 6))

    for target_day in [nigeria_today() + timedelta(days=1), nigeria_today()]:
        target_str = target_day.isoformat()
        async with async_session() as session:
            if tier == "TOP6":
                order = Prediction.rank.asc()
            elif tier == "TOP3":
                order = Prediction.dominance_score.asc()
            else:  # TOP2
                order = Prediction.dominance_score.asc()

            result = await session.execute(
                select(Prediction)
                .where(
                    Prediction.target_date == target_str,
                    Prediction.tier.in_(allowed_tiers),
                    Prediction.passed_consensus.is_(True),
                    Prediction.removed_at_recheck.is_(False),
                )
                .order_by(order)
                .limit(limit)
            )
            rows = list(result.scalars().all())
            if rows:
                return rows
    return []


async def _run_pipeline(api_client: ApiFootballClient, target_day: date) -> dict:
    async with async_session() as session:
        return await run_daily_pipeline(
            session, api_client, target_day=target_day, timezone=settings.timezone
        )


async def _do_scan(send_fn, api_client: ApiFootballClient, target_day: date) -> None:
    """Run pipeline for target_day (in Nigeria time), then send Top 6 picks as a new message."""
    today_ng = nigeria_today()
    label    = "Today" if target_day == today_ng else "Tomorrow"
    day_str  = target_day.strftime("%A, %d %B %Y")

    sent = await send_fn(
        f"⚡ <b>Scanning {label} ({day_str}) Nigeria Time...</b>\n"
        f"Fetching &amp; scoring all fixtures — please wait.",
        parse_mode=PARSE_MODE,
    )
    try:
        result = await _run_pipeline(api_client, target_day)
        total  = result.get("total", 0)
        passed = result.get("passed", 0)
        preds  = await _predictions_for_day(target_day)
        picks_text = format_tier_message("TOP6", preds, target_day=target_day)
        await sent.reply(
            f"✅ <b>Scan complete — {label}</b>\n"
            f"📊 Scanned: <code>{total}</code> fixtures | "
            f"🏆 Cleared gate: <code>{passed}</code> picks\n\n"
            f"{picks_text}",
            parse_mode=PARSE_MODE,
            reply_markup=back_keyboard(),
        )
    except Exception as e:
        err_str = html.escape(str(e)[:300])
        await sent.reply(
            f"❌ <b>Scan error ({label}):</b>\n<code>{err_str}</code>",
            parse_mode=PARSE_MODE,
            reply_markup=back_keyboard(),
        )


# ── Slash commands ─────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await _reg(message)
    await message.answer(WELCOME, parse_mode=PARSE_MODE, reply_markup=main_menu_keyboard())


@router.message(Command("today"))
async def cmd_today(message: Message, api_client: ApiFootballClient) -> None:
    await _reg(message)
    await _do_scan(message.answer, api_client, nigeria_today())


@router.message(Command("tomorrow"))
async def cmd_tomorrow(message: Message, api_client: ApiFootballClient) -> None:
    await _reg(message)
    await _do_scan(message.answer, api_client, nigeria_today() + timedelta(days=1))


@router.message(Command("top6"))
async def cmd_top6(message: Message) -> None:
    await _reg(message)
    preds = await _predictions_by_tier("TOP6")
    await message.answer(format_tier_message("TOP6", preds), parse_mode=PARSE_MODE, reply_markup=back_keyboard())


@router.message(Command("top3"))
async def cmd_top3(message: Message) -> None:
    await _reg(message)
    preds = await _predictions_by_tier("TOP3")
    await message.answer(format_tier_message("TOP3", preds), parse_mode=PARSE_MODE, reply_markup=back_keyboard())


@router.message(Command("top2"))
async def cmd_top2(message: Message) -> None:
    await _reg(message)
    preds = await _predictions_by_tier("TOP2")
    await message.answer(format_tier_message("TOP2", preds), parse_mode=PARSE_MODE, reply_markup=back_keyboard())


@router.message(Command("lock"))
async def cmd_lock(message: Message) -> None:
    await _reg(message)
    preds = await _predictions_by_tier("TOP2")
    await message.answer(format_tier_message("TOP2", preds), parse_mode=PARSE_MODE, reply_markup=back_keyboard())


@router.message(Command("run"))
async def cmd_run(message: Message, api_client: ApiFootballClient) -> None:
    await _reg(message)
    await _do_scan(message.answer, api_client, nigeria_today())
    await _do_scan(message.answer, api_client, nigeria_today() + timedelta(days=1))


# ── Callback query handlers (always send NEW messages) ────────

@router.callback_query(F.data == "cmd_today")
async def cb_today(query: CallbackQuery, api_client: ApiFootballClient) -> None:
    await _reg(query)
    await query.answer("📅 Scanning today's fixtures (Nigeria Time)...")
    await _do_scan(query.message.answer, api_client, nigeria_today())


@router.callback_query(F.data == "cmd_tomorrow")
async def cb_tomorrow(query: CallbackQuery, api_client: ApiFootballClient) -> None:
    await _reg(query)
    await query.answer("🌅 Scanning tomorrow's fixtures (Nigeria Time)...")
    await _do_scan(query.message.answer, api_client, nigeria_today() + timedelta(days=1))


@router.callback_query(F.data == "cmd_top6")
async def cb_top6(query: CallbackQuery) -> None:
    await _reg(query)
    preds = await _predictions_by_tier("TOP6")
    await query.message.answer(format_tier_message("TOP6", preds), parse_mode=PARSE_MODE, reply_markup=back_keyboard())
    await query.answer()


@router.callback_query(F.data == "cmd_top3")
async def cb_top3(query: CallbackQuery) -> None:
    await _reg(query)
    preds = await _predictions_by_tier("TOP3")
    await query.message.answer(format_tier_message("TOP3", preds), parse_mode=PARSE_MODE, reply_markup=back_keyboard())
    await query.answer()


@router.callback_query(F.data == "cmd_top2")
async def cb_top2(query: CallbackQuery) -> None:
    await _reg(query)
    preds = await _predictions_by_tier("TOP2")
    await query.message.answer(format_tier_message("TOP2", preds), parse_mode=PARSE_MODE, reply_markup=back_keyboard())
    await query.answer()
