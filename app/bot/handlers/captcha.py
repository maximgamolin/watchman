import logging

from aiogram import Router, Bot, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.cases.captcha.captcha import CaptchaCase
from app.cases.captcha.dto import GroupMessageUiDto

router = Router(name='captcha')

logger = logging.getLogger(__name__)


@router.message(F.chat.type.in_({'group', 'supergroup'}), ~F.from_user.is_bot)
async def group_message_handler(
    message: Message,
    session: AsyncSession,
    redis_client: aioredis.Redis,
    bot: Bot,
) -> None:
    """
    Хэндлер для всех сообщений из групп.
    Парсит Update → UiDto и передаёт в CaptchaCase.
    """
    dto = GroupMessageUiDto(
        user_id=message.from_user.id,
        group_id=message.chat.id,
        message_id=message.message_id,
        text=message.text or message.caption,
    )

    case = CaptchaCase(session=session, redis_client=redis_client, bot=bot)
    try:
        await case.handle_group_message(dto)
    except Exception as exc:
        logger.error(
            '[group_message_handler] Unhandled error user=%s group=%s: %s',
            dto.user_id, dto.group_id, str(exc),
        )


@router.message()
async def debug_unhandled_message(message: Message) -> None:
    # Диагностика: ловит всё, что не прошло основной фильтр
    logger.info(
        '[DEBUG] chat_type=%s from_user=%s is_bot=%s text=%r',
        message.chat.type,
        message.from_user,
        message.from_user.is_bot if message.from_user else None,
        (message.text or '')[:50],
    )
