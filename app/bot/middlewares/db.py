from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import AsyncSessionFactory


class DatabaseMiddleware(BaseMiddleware):
    """Создаёт AsyncSession для каждого апдейта и кладёт её в data['session']."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with AsyncSessionFactory() as session:
            data['session'] = session
            return await handler(event, data)
