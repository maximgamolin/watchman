import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.dal.deleted_message.dto import DeletedMessageDalDto
from app.domain.user.types import UserID, GroupID, MessageID
from app.infrastructure.db.models.deleted_message import DeletedMessageORM

logger = logging.getLogger(__name__)


class DeletedMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        user_id: UserID,
        group_id: GroupID,
        message_id: MessageID,
        text: str,
        reason: str,
    ) -> None:
        """Сохраняет запись об удалённом сообщении."""
        logger.debug(
            '[DeletedMessageRepository.add] Storing deleted message %s user=%s group=%s reason=%s',
            message_id, user_id, group_id, reason,
        )
        orm_obj = DeletedMessageORM(
            user_id=int(user_id),
            group_id=int(group_id),
            message_id=int(message_id),
            text=text,
            reason=reason,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        logger.info(
            '[DeletedMessageRepository.add] Stored deleted message %s', message_id,
        )
