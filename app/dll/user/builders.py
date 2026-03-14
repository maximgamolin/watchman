from framework.data_logic_layer.builders import ABSEntityFromRepoBuilder
from framework.data_logic_layer.meta import BaseMeta

from app.dal.user.dto import GroupMemberDalDto
from app.domain.user.main import GroupMember


class GroupMemberBuilder(ABSEntityFromRepoBuilder):
    def __init__(self, dal_dto: GroupMemberDalDto) -> None:
        self._dal_dto = dal_dto

    def build_one(self) -> GroupMember:
        dto = self._dal_dto
        member = GroupMember(
            user_id=dto.user_id,
            group_id=dto.group_id,
            is_captcha_passed_flag=dto.is_captcha_passed,
        )
        member.update_meta(BaseMeta(
            id_from_storage=int(dto.user_id),
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            version=dto.version,
        ))
        return member

    def build_many(self) -> list[GroupMember]:
        raise NotImplementedError
