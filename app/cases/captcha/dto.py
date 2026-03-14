from dataclasses import dataclass
from typing import Optional


@dataclass
class GroupMessageUiDto:
    """Входящее сообщение пользователя из группы."""
    user_id: int
    group_id: int
    message_id: int
    # Текст сообщения (None если медиа без подписи)
    text: Optional[str]
