from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from framework.domain.abs import IDTO

from app.domain.user.types import UserID, GroupID


@dataclass
class GroupMemberDalDto(IDTO):
    user_id: UserID
    group_id: GroupID
    is_captcha_passed: bool
    version: int
    created_at: datetime
    updated_at: Optional[datetime]
