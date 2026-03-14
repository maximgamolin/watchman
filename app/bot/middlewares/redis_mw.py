from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

import redis.asyncio as aioredis


class RedisMiddleware(BaseMiddleware):
    """Кладёт Redis-клиент в data['redis_client'] для каждого апдейта."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data['redis_client'] = self._redis
        return await handler(event, data)
