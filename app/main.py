import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers.captcha import router as captcha_router
from app.bot.middlewares.db import DatabaseMiddleware
from app.bot.middlewares.redis_mw import RedisMiddleware
from app.infrastructure.config import settings
from app.infrastructure.redis.client import get_async_redis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    redis_client = get_async_redis()

    # Глобальные middleware (применяются ко всем роутерам)
    dp.message.middleware(DatabaseMiddleware())
    dp.message.middleware(RedisMiddleware(redis_client=redis_client))

    dp.include_router(captcha_router)

    logger.info('Starting watchman bot...')
    try:
        await dp.start_polling(bot, allowed_updates=['message'])
    finally:
        await redis_client.aclose()
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
