import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis

from app.domain.user.types import UserID, GroupID, MessageID

logger = logging.getLogger(__name__)

CAPTCHA_KEY_PREFIX = 'captcha:'


@dataclass
class CaptchaSession:
    """Данные сессии капчи, хранящиеся в Redis."""
    user_id: UserID
    group_id: GroupID
    # Ожидаемое число, которое должен ввести пользователь
    expected_number: int
    # ID сообщения бота с капчей в группе (нужен для удаления)
    captcha_message_id: MessageID
    # Исходное сообщение пользователя
    original_message_id: MessageID
    original_message_text: str
    created_at: datetime


class CaptchaRedisRepository:
    """
    Управляет сессиями капчи в Redis.
    Каждая запись: captcha:{group_id}:{user_id} → JSON.
    Celery-задача находит просроченные записи и чистит их.
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    @staticmethod
    def _make_key(group_id: GroupID, user_id: UserID) -> str:
        return f'{CAPTCHA_KEY_PREFIX}{int(group_id)}:{int(user_id)}'

    async def fetch(self, user_id: UserID, group_id: GroupID) -> Optional[CaptchaSession]:
        """Возвращает активную сессию капчи или None, если не найдена."""
        key = self._make_key(group_id, user_id)

        logger.debug('[CaptchaRedisRepository.fetch] Попытка получить сессию капчи key=%s', key)
        raw = await self._redis.get(key)
        logger.info('[CaptchaRedisRepository.fetch] Сессия капчи получена key=%s found=%s', key, raw is not None)

        if raw is None:
            return None
        data = json.loads(raw)
        return CaptchaSession(
            user_id=UserID(data['user_id']),
            group_id=GroupID(data['group_id']),
            expected_number=data['expected_number'],
            captcha_message_id=MessageID(data['captcha_message_id']),
            original_message_id=MessageID(data['original_message_id']),
            original_message_text=data.get('original_message_text', ''),
            created_at=datetime.fromisoformat(data['created_at']),
        )

    async def create(
        self,
        user_id: UserID,
        group_id: GroupID,
        expected_number: int,
        captcha_message_id: MessageID,
        original_message_id: MessageID,
        original_message_text: str,
    ) -> CaptchaSession:
        """Сохраняет сессию капчи в Redis."""
        key = self._make_key(group_id, user_id)
        now = datetime.now(timezone.utc)
        data = {
            'user_id': int(user_id),
            'group_id': int(group_id),
            'expected_number': expected_number,
            'captcha_message_id': int(captcha_message_id),
            'original_message_id': int(original_message_id),
            'original_message_text': original_message_text,
            'created_at': now.isoformat(),
        }

        logger.debug('[CaptchaRedisRepository.create] Попытка сохранить сессию капчи key=%s number=%d', key, expected_number)
        await self._redis.set(key, json.dumps(data))
        logger.info('[CaptchaRedisRepository.create] Сессия капчи сохранена key=%s number=%d', key, expected_number)

        return CaptchaSession(
            user_id=user_id,
            group_id=group_id,
            expected_number=expected_number,
            captcha_message_id=captcha_message_id,
            original_message_id=original_message_id,
            original_message_text=original_message_text,
            created_at=now,
        )

    async def delete(self, user_id: UserID, group_id: GroupID) -> None:
        """Удаляет сессию капчи из Redis (после успешного прохождения или истечения)."""
        key = self._make_key(group_id, user_id)

        logger.debug('[CaptchaRedisRepository.delete] Попытка удалить сессию капчи key=%s', key)
        await self._redis.delete(key)
        logger.info('[CaptchaRedisRepository.delete] Сессия капчи удалена key=%s', key)
