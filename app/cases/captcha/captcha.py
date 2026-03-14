import logging
import random

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.cases.captcha.dto import GroupMessageUiDto
from app.dll.user.uow import GroupMemberUOW
from app.domain.user.main import GroupMember
from app.domain.user.types import UserID, GroupID, MessageID

logger = logging.getLogger(__name__)


class CaptchaCase:
    """
    Связующий слой: обрабатывает входящие сообщения из группы.

    Сценарии:
    1. Новый пользователь (нет в БД, нет в Redis) → создать GroupMember + отправить капчу.
    2. Пользователь с активной капчей (БД is_captcha_passed=False + запись в Redis):
       - Ввёл верное число → пометить пройденным, удалить сессию капчи.
       - Написал что-то ещё → удалить сообщение, сохранить в deleted_message.
    3. Нет сессии в Redis, но БД is_captcha_passed=False → предыдущая капча истекла,
       пользователь пишет снова → выдать новую капчу.
    4. Пользователь уже прошёл капчу → пропустить.
    """

    def __init__(
        self,
        session: AsyncSession,
        redis_client: aioredis.Redis,
        bot: Bot,
        uow_cls=GroupMemberUOW,
    ) -> None:
        self._uow = uow_cls(session=session, redis_client=redis_client)
        self._bot = bot

    async def handle_group_message(self, dto: GroupMessageUiDto) -> None:
        user_id, group_id, message_id, text = self._convert_message_dto(dto)

        logger.debug(
            '[CaptchaCase.handle_group_message] user=%s group=%s msg=%s',
            user_id, group_id, message_id,
        )

        async with self._uow:
            member = await self._uow.fetch_group_member_or_none(user_id, group_id)

            if member is None:
                # Первое сообщение пользователя в этой группе
                await self._handle_new_user(user_id, group_id, message_id, text)
                return

            if member.is_captcha_passed():
                logger.debug(
                    '[CaptchaCase.handle_group_message] User %s already passed captcha', user_id,
                )
                return

            # Капча ещё не пройдена — проверяем активную сессию в Redis
            captcha_session = await self._uow.fetch_captcha(user_id, group_id)

            if captcha_session is None:
                # Предыдущая сессия истекла, пользователь пишет снова — выдаём новую капчу
                await self._send_new_captcha(
                    member=member,
                    user_id=user_id,
                    group_id=group_id,
                    message_id=message_id,
                    text=text,
                    is_new_member=False,
                )
                return

            # Сессия активна — проверяем ответ пользователя
            answer = text.strip()
            if answer == str(captcha_session.expected_number):
                await self._pass_captcha(
                    member=member,
                    user_id=user_id,
                    group_id=group_id,
                    answer_message_id=message_id,
                    captcha_message_id=captcha_session.captcha_message_id,
                )
            else:
                # Неверный ответ или произвольный текст — удаляем и сохраняем в лог
                await self._delete_message_and_store(
                    user_id=user_id,
                    group_id=group_id,
                    message_id=message_id,
                    text=text,
                    reason='spam_during_captcha',
                )

    # ── Приватные методы ─────────────────────────────────────────────────────

    @staticmethod
    def _convert_message_dto(
        dto: GroupMessageUiDto,
    ) -> tuple['UserID', 'GroupID', 'MessageID', str]:
        """Конвертирует примитивы UiDto в доменные типы."""
        return (
            UserID(dto.user_id),
            GroupID(dto.group_id),
            MessageID(dto.message_id),
            dto.text or '',
        )

    async def _handle_new_user(
        self,
        user_id: UserID,
        group_id: GroupID,
        message_id: MessageID,
        text: str,
    ) -> None:
        """Создаёт нового GroupMember (is_captcha_passed=False) и отправляет капчу."""
        new_member = GroupMember.initialize_new_member(user_id=user_id, group_id=group_id)
        self._uow.add_member_for_save(new_member)
        await self._uow.commit()

        await self._send_new_captcha(
            member=new_member,
            user_id=user_id,
            group_id=group_id,
            message_id=message_id,
            text=text,
            is_new_member=True,
        )

    async def _send_new_captcha(
        self,
        member: GroupMember,
        user_id: UserID,
        group_id: GroupID,
        message_id: MessageID,
        text: str,
        is_new_member: bool,
    ) -> None:
        """Генерирует случайное число, отправляет реплай с капчей, сохраняет сессию в Redis."""
        expected_number = random.randint(0, 9)

        logger.info(
            '[CaptchaCase._send_new_captcha] Sending captcha to user=%s group=%s number=%d',
            user_id, group_id, expected_number,
        )

        captcha_msg = await self._bot.send_message(
            chat_id=int(group_id),
            text=(
                f'Привет! Чтобы писать в этой группе, пройди проверку.\n'
                f'Введи число: <b>{expected_number}</b>'
            ),
            reply_to_message_id=int(message_id),
            parse_mode='HTML',
        )

        await self._uow.create_captcha(
            user_id=user_id,
            group_id=group_id,
            expected_number=expected_number,
            captcha_message_id=MessageID(captcha_msg.message_id),
            original_message_id=message_id,
            original_message_text=text,
        )

    async def _pass_captcha(
        self,
        member: GroupMember,
        user_id: UserID,
        group_id: GroupID,
        answer_message_id: MessageID,
        captcha_message_id: MessageID,
    ) -> None:
        """Помечает участника как прошедшего капчу, удаляет оба сообщения и сессию из Redis."""
        logger.info(
            '[CaptchaCase._pass_captcha] User %s passed captcha in group %s', user_id, group_id,
        )
        member.mark_captcha_passed()
        self._uow.add_member_for_save(member)
        await self._uow.commit()

        await self._uow.delete_captcha(user_id, group_id)

        # Удаляем сообщение пользователя с ответом и сообщение бота с капчей
        try:
            await self._bot.delete_message(chat_id=int(group_id), message_id=int(answer_message_id))
        except Exception as exc:
            logger.warning('[CaptchaCase._pass_captcha] Could not delete answer msg=%s: %s', answer_message_id, exc)
        try:
            await self._bot.delete_message(chat_id=int(group_id), message_id=int(captcha_message_id))
        except Exception as exc:
            logger.warning('[CaptchaCase._pass_captcha] Could not delete captcha msg=%s: %s', captcha_message_id, exc)

    async def _delete_message_and_store(
        self,
        user_id: UserID,
        group_id: GroupID,
        message_id: MessageID,
        text: str,
        reason: str,
    ) -> None:
        """Удаляет сообщение через Telegram API и сохраняет его в таблицу deleted_message."""
        logger.info(
            '[CaptchaCase._delete_message_and_store] Deleting msg=%s reason=%s', message_id, reason,
        )
        try:
            await self._bot.delete_message(chat_id=int(group_id), message_id=int(message_id))
        except Exception as exc:
            logger.warning(
                '[CaptchaCase._delete_message_and_store] Could not delete msg=%s: %s',
                message_id, str(exc),
            )

        await self._uow.store_deleted_message(
            user_id=user_id,
            group_id=group_id,
            message_id=message_id,
            text=text,
            reason=reason,
        )
