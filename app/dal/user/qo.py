from dataclasses import dataclass, field
from typing import Optional, Union

from framework.data_access_layer.query_object.base import ABSQueryObject
from framework.data_access_layer.values import Empty

from app.domain.user.types import UserID, GroupID


@dataclass
class GroupMemberQO(ABSQueryObject):
    user_id: Optional[Union[UserID, Empty]] = field(default_factory=Empty)
    group_id: Optional[Union[GroupID, Empty]] = field(default_factory=Empty)
    is_captcha_passed: Optional[Union[bool, Empty]] = field(default_factory=Empty)
