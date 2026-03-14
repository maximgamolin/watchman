import logging
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from framework.data_access_layer.values import Empty

from app.dal.user.dto import GroupMemberDalDto
from app.dal.user.qo import GroupMemberQO
from app.domain.user.main import GroupMember
from app.domain.user.types import UserID, GroupID
from app.exceptions.user import GroupMemberNotFound, OptimisticLockError
from app.infrastructure.db.models.user import GroupMemberORM

logger = logging.getLogger(__name__)


class GroupMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def fetch_one(self, filter_params: GroupMemberQO) -> GroupMemberDalDto:
        logger.debug('[GroupMemberRepository.fetch_one] Попытка получить участника группы: %s', filter_params)
        stmt = select(GroupMemberORM)
        stmt = self._apply_filters(stmt, filter_params)
        result = await self._session.execute(stmt)
        orm_obj = result.scalar_one_or_none()
        if orm_obj is None:
            logger.warning('[GroupMemberRepository.fetch_one] Участник группы не найден')
            raise GroupMemberNotFound()
        logger.info('[GroupMemberRepository.fetch_one] Участник группы получен user=%s group=%s',
                    orm_obj.user_id, orm_obj.group_id)
        return self._orm_to_dto(orm_obj)

    async def fetch_one_or_none(self, filter_params: GroupMemberQO) -> Optional[GroupMemberDalDto]:
        logger.debug('[GroupMemberRepository.fetch_one_or_none] Попытка получить участника группы: %s', filter_params)
        stmt = select(GroupMemberORM)
        stmt = self._apply_filters(stmt, filter_params)
        result = await self._session.execute(stmt)
        orm_obj = result.scalar_one_or_none()
        logger.info('[GroupMemberRepository.fetch_one_or_none] Результат получен found=%s', orm_obj is not None)
        if orm_obj is None:
            return None
        return self._orm_to_dto(orm_obj)

    async def add(self, member: GroupMember) -> GroupMemberDalDto:
        logger.debug('[GroupMemberRepository.add] Попытка добавить участника user=%s group=%s',
                     member.get_user_id(), member.get_group_id())
        orm_obj = self._domain_to_orm(member)
        self._session.add(orm_obj)
        await self._session.flush()
        logger.info('[GroupMemberRepository.add] Участник добавлен user=%s group=%s',
                    orm_obj.user_id, orm_obj.group_id)
        return self._orm_to_dto(orm_obj)

    async def update_one(self, member: GroupMember) -> GroupMemberDalDto:
        """
        Обновляет участника группы с оптимистичной блокировкой.

        Выполняется один UPDATE с фильтром по (user_id, group_id, version).
        Если строка не найдена — версия устарела (другой поток изменил запись),
        выбрасывается OptimisticLockError.
        При успехе version инкрементируется на 1.
        """
        current_version = member.get_version()
        if current_version is None:
            raise OptimisticLockError(
                f'Версия не задана для user={member.get_user_id()} group={member.get_group_id()}'
            )

        logger.debug(
            '[GroupMemberRepository.update_one] Попытка обновить участника user=%s group=%s version=%d',
            member.get_user_id(), member.get_group_id(), current_version,
        )

        stmt = (
            update(GroupMemberORM)
            .where(
                GroupMemberORM.user_id == int(member.get_user_id()),
                GroupMemberORM.group_id == int(member.get_group_id()),
                # Оптимистичная блокировка: совпадает только если никто не менял запись
                GroupMemberORM.version == current_version,
            )
            .values(
                is_captcha_passed=member.is_captcha_passed(),
                version=current_version + 1,
            )
            .returning(GroupMemberORM)
        )

        result = await self._session.execute(stmt)
        orm_obj = result.scalar_one_or_none()

        if orm_obj is None:
            # UPDATE не затронул ни одной строки — версия устарела
            logger.warning(
                '[GroupMemberRepository.update_one] Конфликт версий user=%s group=%s version=%d',
                member.get_user_id(), member.get_group_id(), current_version,
            )
            raise OptimisticLockError(
                f'Конфликт версий: user={member.get_user_id()} group={member.get_group_id()} '
                f'ожидалась version={current_version}'
            )

        logger.info(
            '[GroupMemberRepository.update_one] Участник обновлён user=%s group=%s новая version=%d',
            orm_obj.user_id, orm_obj.group_id, orm_obj.version,
        )
        return self._orm_to_dto(orm_obj)

    # ── Приватные методы ─────────────────────────────────────────────────────

    def _apply_filters(self, stmt, qo: GroupMemberQO):
        if not isinstance(qo.user_id, Empty):
            stmt = stmt.where(GroupMemberORM.user_id == int(qo.user_id))
        if not isinstance(qo.group_id, Empty):
            stmt = stmt.where(GroupMemberORM.group_id == int(qo.group_id))
        if not isinstance(qo.is_captcha_passed, Empty):
            stmt = stmt.where(GroupMemberORM.is_captcha_passed == qo.is_captcha_passed)
        return stmt

    def _orm_to_dto(self, orm_obj: GroupMemberORM) -> GroupMemberDalDto:
        return GroupMemberDalDto(
            user_id=UserID(orm_obj.user_id),
            group_id=GroupID(orm_obj.group_id),
            is_captcha_passed=orm_obj.is_captcha_passed,
            version=orm_obj.version,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def _domain_to_orm(self, member: GroupMember) -> GroupMemberORM:
        return GroupMemberORM(
            user_id=int(member.get_user_id()),
            group_id=int(member.get_group_id()),
            is_captcha_passed=member.is_captcha_passed(),
            version=0,  # новая запись всегда начинает с версии 0
        )
