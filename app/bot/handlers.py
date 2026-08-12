"""
Telegram bot command handlers with inline keyboards.

Flow:
  📅 Today button    → scan API for today + show ELITE picks
  🌅 Tomorrow button → scan API for tomorrow + show ELITE picks
  🏆 Top 6           → show top 6 from already-scanned results (DB)
  🥇 Top 3           → show top 3 from already-scanned results (DB)
  🔒 Top 2           → show top 2 from already-scanned results (DB)

All results are posted as NEW messages — existing messages are never deleted.
"""
import html
from datetime import date, datetime, timedelta

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

WELCOME = (
    f"{HEADER}\n\n"
    "🎯 <b>Automated match screening</b>\n\n"
    "Only fixtures scoring <b>NO-3 ≥ 85</b> <i>and</i> <b>Safety = 100</b> make the list — "
    "everything else is dropped.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "📅 <b>Today</b> — Scan &amp; show today's ELITE picks\n"
    "🌅 <b>Tomorrow</b> — Scan &amp; show tomorrow's ELITE picks\n"
    "🏆 <b>Top 6</b> — Best 6 picks from last scan\n"
    "🥇 <b>Top 3</b> — Best 3 picks from last scan\n"
    "🔒 <b>Top 2</b> — Safest 2 locks from last scan\n\n"
    "Or use commands: <code>/today</code> <code>/tomorrow</code> "
    "<code>/top6</code> <code>/top3</code> <code>/top2</code> <code>/run</code>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🔔 <i>Auto-scan + broadcast runs every night at 10:00 PM.</i>\n"
)


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
    start = datetime.combine(target_day, datetime.min.time())
    end = start + timedelta(days=1)
    async with async_session() as session:
        result = await session.execute(
            select(Prediction)
            .where(
                Prediction.kickoff >= start,
                Prediction.kickoff < end,
                Prediction.tier.in_(["TOP2", "TOP3", "TOP6"]),
                Prediction.passed_consensus.is_(True),
                Prediction.removed_at_recheck.is_(False),
            )
            .order_by(Prediction.rank.asc())
        )
        return list(result.scalars().all())


async def _predictions_by_tier(tier: str) -> list[Prediction]:
    """
    Return predictions for the given tier from the most recent scan day
    (prefer tomorrow, then today).
    Strict hierarchy:
      - TOP6 includes TOP2, TOP3, TOP6
      - TOP3 includes TOP2, TOP3 (sieved from TOP6)
      - TOP2 includes TOP2 (sieved from TOP3)
    """
    tier_filters = {
        "TOP6": ["TOP2", "TOP3", "TOP6"],
        "TOP3": ["TOP2", "TOP3"],
        "TOP2": ["TOP2"],
    }
    allowed_tiers = tier_filters.get(tier, [tier])

    for target_day in [date.today() + timedelta(days=1), date.today()]:
        start = datetime.combine(target_day, datetime.min.time())
        end = start + timedelta(days=1)
        async with async_session() as session:
            query = select(Prediction).where(
                Prediction.kickoff >= start,
                Prediction.kickoff < end,
                Prediction.tier.in_(allowed_tiers),
                Prediction.passed_consensus.is_(True),
                Prediction.removed_at_recheck.is_(False),
            )
            if tier == "TOP6":
                query = query.order_by(Prediction.rank.asc())
            elif tier == "TOP3":
                query = query.order_by(Prediction.dominance_score.asc(), Prediction.no3_score.desc())
            elif tier == "TOP2":
                query = query.order_by(Prediction.dominance_score.asc(), Prediction.safety_score.desc(), Prediction.no3_score.desc())
            else:
                query = query.order_by(Prediction.rank.asc())

            result = await session.execute(query)
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
    """Run pipeline for target_day, then send picks as a new message."""
    label = "Today" if target_day == date.today() else "Tomorrow"
    day_str = target_day.strftime("%A, %d %B %Y")

    sent = await send_fn(
        f"⚡ <b>Scanning {label} ({day_str})...</b>\n"
        f"Fetching &amp; scoring all fixtures — this may take a minute or two.",
        parse_mode=PARSE_MODE,
    )
    try:
        result = await _run_pipeline(api_client, target_day)
        total = result.get("total", 0)
        passed = result.get("passed", 0)
        preds = await _predictions_for_day(target_day)
        picks_text = format_tier_message("TOP6", preds)
        await sent.reply(
            f"✅ <b>Scan complete — {label}</b>\n"
            f"📊 Scanned: <code>{total}</code> fixtures | 🏆 Cleared gate: <code>{passed}</code> picks\n\n"
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
    await _do_scan(message.answer, api_client, date.today())


@router.message(Command("tomorrow"))
async def cmd_tomorrow(message: Message, api_client: ApiFootballClient) -> None:
    await _reg(message)
    await _do_scan(message.answer, api_client, date.today() + timedelta(days=1))


@router.message(Command("top6"))
async def cmd_top6(message: Message) -> None:
    await _reg(message)
    preds = await _predictions_by_tier("TOP6")
    await message.answer(
        format_tier_message("TOP6", preds),
        parse_mode=PARSE_MODE,
        reply_markup=back_keyboard(),
    )


@router.message(Command("top3"))
async def cmd_top3(message: Message) -> None:
    await _reg(message)
    preds = await _predictions_by_tier("TOP3")
    await message.answer(
        format_tier_message("TOP3", preds),
        parse_mode=PARSE_MODE,
        reply_markup=back_keyboard(),
    )


@router.message(Command("top2"))
async def cmd_top2(message: Message) -> None:
    await _reg(message)
    preds = await _predictions_by_tier("TOP2")
    await message.answer(
        format_tier_message("TOP2", preds),
        parse_mode=PARSE_MODE,
        reply_markup=back_keyboard(),
    )


@router.message(Command("lock"))
async def cmd_lock(message: Message) -> None:
    await _reg(message)
    preds = await _predictions_by_tier("TOP2")
    await message.answer(
        format_tier_message("TOP2", preds),
        parse_mode=PARSE_MODE,
        reply_markup=back_keyboard(),
    )


@router.message(Command("run"))
async def cmd_run(message: Message, api_client: ApiFootballClient) -> None:
    await _reg(message)
    await _do_scan(message.answer, api_client, date.today())
    await _do_scan(message.answer, api_client, date.today() + timedelta(days=1))


# ── Callback query handlers (always send NEW messages, nothing replaced) ──

@router.callback_query(F.data == "cmd_today")
async def cb_today(query: CallbackQuery, api_client: ApiFootballClient) -> None:
    await _reg(query)
    await query.answer("📅 Scanning today's fixtures...")
    await _do_scan(query.message.answer, api_client, date.today())


@router.callback_query(F.data == "cmd_tomorrow")
async def cb_tomorrow(query: CallbackQuery, api_client: ApiFootballClient) -> None:
    await _reg(query)
    await query.answer("🌅 Scanning tomorrow's fixtures...")
    await _do_scan(query.message.answer, api_client, date.today() + timedelta(days=1))


@router.callback_query(F.data == "cmd_top6")
async def cb_top6(query: CallbackQuery) -> None:
    await _reg(query)
    preds = await _predictions_by_tier("TOP6")
    await query.message.answer(
        format_tier_message("TOP6", preds),
        parse_mode=PARSE_MODE,
        reply_markup=back_keyboard(),
    )
    await query.answer()


@router.callback_query(F.data == "cmd_top3")
async def cb_top3(query: CallbackQuery) -> None:
    await _reg(query)
    preds = await _predictions_by_tier("TOP3")
    await query.message.answer(
        format_tier_message("TOP3", preds),
        parse_mode=PARSE_MODE,
        reply_markup=back_keyboard(),
    )
    await query.answer()


@router.callback_query(F.data == "cmd_top2")
async def cb_top2(query: CallbackQuery) -> None:
    await _reg(query)
    preds = await _predictions_by_tier("TOP2")
    await query.message.answer(
        format_tier_message("TOP2", preds),
        parse_mode=PARSE_MODE,
        reply_markup=back_keyboard(),
    )
    await query.answer()
