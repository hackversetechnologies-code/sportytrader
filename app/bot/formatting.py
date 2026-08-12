"""
Message formatting helpers for Telegram output using HTML parse mode.

Sport-themed ELITE badge format with rich emoji and clean layout.
Every prediction that reaches this formatter already cleared the hard gate
(NO-3 >= 85 AND Safety == 100), so every entry is labeled ELITE.
"""
import html
from datetime import date
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.models import Prediction

TIER_TITLES = {
    "TOP6": "TOP 6 ELITE PICKS",
    "TOP3": "TOP 3 BEST PICKS",
    "TOP2": "TOP 2 SAFEST LOCKS",
}

TIER_EMOJIS = {
    "TOP6": "🏆",
    "TOP3": "🥇",
    "TOP2": "🔒",
}

RANK_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

HEADER = "⚽ <b>NO-3 ENGINE</b> ⚽"


def format_tier_message(tier_key: str, predictions: list[Prediction]) -> str:
    title = TIER_TITLES.get(tier_key, tier_key)
    icon = TIER_EMOJIS.get(tier_key, "🏅")

    if not predictions:
        return (
            f"{HEADER}\n\n"
            f"{icon} <b>{html.escape(title)}</b>\n\n"
            f"⏳ No fixtures currently clear the\n"
            f"85% NO-3 / 100% Safety gate.\n\n"
            f"<i>Daily scan runs at 10:00 PM. Use /run or the button below to trigger now.</i>"
        )

    lines = [
        HEADER,
        "",
        f"{icon} <b>{html.escape(title)}</b>",
        f"📅 <i>{html.escape(date.today().strftime('%A, %d %B %Y'))}</i>",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    for i, p in enumerate(predictions, start=1):
        medal = RANK_MEDALS.get(i, f"#{i}")
        kickoff = p.kickoff.strftime("%H:%M") if p.kickoff else "?"
        no3 = f"{p.no3_score:.1f}"
        safety = f"{p.safety_score:.0f}"
        home = html.escape(p.home_team)
        away = html.escape(p.away_team)
        league = html.escape(p.league_name)

        lines.append("")
        lines.append(f"{medal} <b>{home} vs {away}</b>")
        lines.append(f"🏟️ {league}  ⏰ {kickoff}")
        lines.append(
            f"📊 NO-3: <code>{no3}</code> | 🛡️ Safety: <code>{safety}</code> | 🏷️ <code>ELITE</code>"
        )

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")

    avg = sum(p.no3_score for p in predictions) / len(predictions)
    lines.append(f"📈 Avg Confidence: <code>{avg:.0f}%</code> | Total: <code>{len(predictions)}</code>")
    lines.append("")
    lines.append("<i>All picks cleared NO-3 ≥ 85 & Safety = 100</i>")

    return "\n".join(lines)


def format_prediction_detail(p: Prediction) -> str:
    kickoff_str = p.kickoff.strftime('%Y-%m-%d %H:%M') if p.kickoff else '?'
    home = html.escape(p.home_team)
    away = html.escape(p.away_team)
    league = html.escape(p.league_name)
    tier = html.escape(p.tier or '-')
    return (
        f"⚽ <b>{home} vs {away}</b>\n"
        f"🏟️ {league}\n"
        f"⏰ {kickoff_str}\n\n"
        f"📊 NO-3 Score: <code>{p.no3_score:.1f}</code>\n"
        f"⚡ Dominance: <code>{p.dominance_score:.1f}</code>\n"
        f"🛡️ Safety: <code>{p.safety_score:.0f}</code>\n"
        f"🏷️ Tier: <code>ELITE ({tier})</code>"
    )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main navigation inline keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Today", callback_data="cmd_today"),
            InlineKeyboardButton(text="🌅 Tomorrow", callback_data="cmd_tomorrow"),
        ],
        [
            InlineKeyboardButton(text="🏆 Top 6", callback_data="cmd_top6"),
            InlineKeyboardButton(text="🥇 Top 3", callback_data="cmd_top3"),
            InlineKeyboardButton(text="🔒 Top 2", callback_data="cmd_top2"),
        ],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    """Navigation keyboard shown after results."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Today", callback_data="cmd_today"),
            InlineKeyboardButton(text="🌅 Tomorrow", callback_data="cmd_tomorrow"),
        ],
        [
            InlineKeyboardButton(text="🏆 Top 6", callback_data="cmd_top6"),
            InlineKeyboardButton(text="🥇 Top 3", callback_data="cmd_top3"),
            InlineKeyboardButton(text="🔒 Top 2", callback_data="cmd_top2"),
        ],
    ])
