"""Main Telegram bot file."""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from backend.config import settings
from backend.db import init_db
from backend.bot.handlers import get_router
from backend.scheduler import start_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for bot."""
    # Initialize database
    await init_db(settings.db_path)
    logger.info("Database initialized")

    # Create bot and dispatcher
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Register handlers
    dp.include_router(get_router())
    logger.info("Handlers registered")

    # Start scheduler in background
    scheduler = start_scheduler()
    logger.info("Scheduler started")

    # Start bot
    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
