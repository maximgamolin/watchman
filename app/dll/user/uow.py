import logging
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from framework.data_logic_layer.uow import BaseUnitOfWork

from app.dal.deleted_message.repo import DeletedMessageRepository
from app.dal.user.qo import GroupMemberQO
from app.dal.user.repo import GroupMemberRepository
from app.dll.captcha.redis_repo import CaptchaRedisRepository, CaptchaSession
from app.dll.user.builders import GroupMemberBuilder
from app.domain.user.main import GroupMember
from app.domain.user.types import UserID, GroupID, MessageID
from app.exceptions.user import GroupMemberNotFound

logger = logging.getLogger(__name__)


class GroupMemberUOW(BaseUnitOfWork):
    def __init__(
        self,
        session: AsyncSession,
        redis_client: aioredis.Redis,
        member_repo_cls=GroupMemberRepository,
        deleted_msg_repo_cls=DeletedMessageRepository,
        captcha_repo_cls=CaptchaRedisRepository,
    ) -> None:
        self._session = session
        self._member_repo = member_repo_cls(session)
        self._deleted_msg_repo = deleted_msg_repo_cls(session)
        self._captcha_repo = captcha_repo_cls(redis_client=redis_client)
        self._members_for_save: list[GroupMember] = []

    async def __aenter__(self) -> 'GroupMemberUOW':
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type:
            await self._session.rollback()
        return False

    # ── Fetch ────────────────────────────────────────────────────────────────

    async def fetch_group_member(self, user_id: UserID, group_id: GroupID) -> GroupMember:
        logger.debug('[GroupMemberUOW.fetch_group_member] user=%s group=%s', user_id, group_id)
        try:
            dal_dto = await self._member_repo.fetch_one(
                GroupMemberQO(user_id=user_id, group_id=group_id)
            )
            result = GroupMemberBuilder(dal_dto=dal_dto).build_one()
            logger.info('[GroupMemberUOW.fetch_group_member] Found user=%s group=%s', user_id, group_id)
            return result
        except GroupMemberNotFound:
            logger.debug('[GroupMemberUOW.fetch_group_member] Not found user=%s group=%s', user_id, group_id)
            raise

    async def fetch_group_member_or_none(
        self, user_id: UserID, group_id: GroupID
    ) -> Optional[GroupMember]:
        logger.debug('[GroupMemberUOW.fetch_group_member_or_none] user=%s group=%s', user_id, group_id)
        dal_dto = await self._member_repo.fetch_one_or_none(
            GroupMemberQO(user_id=user_id, group_id=group_id)
        )
        if dal_dto is None:
            return None
        return GroupMemberBuilder(dal_dto=dal_dto).build_one()

    # ── Register for save ────────────────────────────────────────────────────

    def add_member_for_save(self, member: GroupMember) -> None:
        member.set_updated_at_as_now()
        self._members_for_save.append(member)

    # ── Commit ───────────────────────────────────────────────────────────────

    async def commit(self) -> None:
        logger.debug('[GroupMemberUOW.commit] Saving %d member(s)', len(self._members_for_save))
        for member in self._members_for_save:
            if member.is_new():
                await self._member_repo.add(member)
            else:
                await self._member_repo.update_one(member)
        await self._session.commit()
        self._members_for_save = []
        logger.debug('[GroupMemberUOW.commit] Committed')

    # ── Captcha (Redis) ──────────────────────────────────────────────────────

    async def fetch_captcha(self, user_id: UserID, group_id: GroupID) -> Optional[CaptchaSession]:
        """Возвращает активную сессию капчи из Redis или None."""
        logger.debug('[GroupMemberUOW.fetch_captcha] user=%s group=%s', user_id, group_id)
        return await self._captcha_repo.fetch(user_id, group_id)

    async def create_captcha(
        self,
        user_id: UserID,
        group_id: GroupID,
        expected_number: int,
        captcha_message_id: MessageID,
        original_message_id: MessageID,
        original_message_text: str,
    ) -> CaptchaSession:
        """Сохраняет новую сессию капчи в Redis."""
        logger.debug('[GroupMemberUOW.create_captcha] user=%s group=%s', user_id, group_id)
        return await self._captcha_repo.create(
            user_id=user_id,
            group_id=group_id,
            expected_number=expected_number,
            captcha_message_id=captcha_message_id,
            original_message_id=original_message_id,
            original_message_text=original_message_text,
        )

    async def delete_captcha(self, user_id: UserID, group_id: GroupID) -> None:
        """Удаляет сессию капчи из Redis после прохождения или истечения."""
        logger.debug('[GroupMemberUOW.delete_captcha] user=%s group=%s', user_id, group_id)
        await self._captcha_repo.delete(user_id, group_id)

    # ── Deleted messages ─────────────────────────────────────────────────────

    async def store_deleted_message(
        self,
        user_id: UserID,
        group_id: GroupID,
        message_id: MessageID,
        text: str,
        reason: str,
    ) -> None:
        """Сохраняет удалённое сообщение пользователя и сразу коммитит."""
        logger.debug('[GroupMemberUOW.store_deleted_message] msg=%s reason=%s', message_id, reason)
        await self._deleted_msg_repo.add(
            user_id=user_id,
            group_id=group_id,
            message_id=message_id,
            text=text,
            reason=reason,
        )
        await self._session.commit()
        logger.info('[GroupMemberUOW.store_deleted_message] Stored msg=%s', message_id)
