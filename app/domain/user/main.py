from framework.data_logic_layer.meta import MetaManipulation, BaseMeta

from app.domain.user.types import UserID, GroupID


class GroupMember(MetaManipulation):
    """
    Агрегат: участник группы (Telegram-пользователь в конкретном чате).
    Хранит факт прохождения капчи.
    Мультитенантность: один пользователь может быть участником нескольких групп.
    """

    def __init__(
        self,
        user_id: UserID,
        group_id: GroupID,
        is_captcha_passed_flag: bool,
    ) -> None:
        self._user_id = user_id
        self._group_id = group_id
        self._is_captcha_passed_flag = is_captcha_passed_flag
        self._meta = BaseMeta()

    # ── Фабричный метод ─────────────────────────────────────────────────────

    @classmethod
    def initialize_new_member(cls, user_id: UserID, group_id: GroupID) -> 'GroupMember':
        """Создаёт нового участника группы. Капча считается не пройденной."""
        member = cls(
            user_id=user_id,
            group_id=group_id,
            is_captcha_passed_flag=False,
        )
        member.mark_changed()
        return member

    # ── Геттеры ─────────────────────────────────────────────────────────────

    def get_user_id(self) -> UserID:
        return self._user_id

    def get_group_id(self) -> GroupID:
        return self._group_id

    def replace_id_from_meta(self) -> None:
        pass

    # ── Предикаты ───────────────────────────────────────────────────────────

    def is_captcha_passed(self) -> bool:
        """True — пользователь прошёл капчу и допущен в группу."""
        return self._is_captcha_passed_flag

    # ── Мутаторы ────────────────────────────────────────────────────────────

    def mark_captcha_passed(self) -> None:
        """Отмечает, что пользователь успешно прошёл капчу."""
        self._is_captcha_passed_flag = True
        self.mark_changed()
