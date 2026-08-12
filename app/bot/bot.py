"""Aiogram Bot + Dispatcher construction."""
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import get_settings
from app.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

bot = Bot(token=settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


async def register_user(chat_id: int, username: str | None = None, first_name: str | None = None) -> None:
    """Save/update a user's chat ID for broadcasts."""
    from app.database import async_session, get_insert_stmt
    from app.models import TelegramUser

    async with async_session() as session:
        stmt = get_insert_stmt(TelegramUser).values(
            chat_id=chat_id,
            username=username,
            first_name=first_name,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["chat_id"],
            set_={"username": username, "first_name": first_name},
        )
        await session.execute(stmt)
        await session.commit()


async def send_alert(text: str, chat_id: str | None = None, reply_markup=None) -> None:
    """Send alert/broadcast to env chat IDs + all registered Telegram users in DB."""
    from sqlalchemy import select
    from app.database import async_session
    from app.models import TelegramUser

    target_chat_ids = set()

    # Add IDs from settings (.env)
    for tid in settings.telegram_chat_id.split(","):
        tid = tid.strip()
        if tid:
            try:
                target_chat_ids.add(int(tid))
            except ValueError:
                pass

    # Add all registered Telegram users from DB
    try:
        async with async_session() as session:
            result = await session.execute(select(TelegramUser.chat_id))
            for cid in result.scalars().all():
                target_chat_ids.add(cid)
    except Exception as e:
        logger.warning("Could not fetch telegram users from DB for broadcast: %s", e)

    # Broadcast to all unique target chat IDs
    for cid in target_chat_ids:
        try:
            await bot.send_message(cid, text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        except Exception as err:
            logger.warning("Failed to send message to chat_id %s: %s", cid, err)
