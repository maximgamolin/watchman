from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from framework.domain.abs import IDTO

from app.domain.user.types import UserID, GroupID, MessageID


@dataclass
class DeletedMessageDalDto(IDTO):
    user_id: UserID
    group_id: GroupID
    message_id: MessageID
    text: Optional[str]
    reason: str
    deleted_at: datetime
