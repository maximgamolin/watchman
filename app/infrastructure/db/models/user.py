from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class GroupMemberORM(Base):
    __tablename__ = 'group_member'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Telegram user_id
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    # Telegram chat_id (group)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    # True — пользователь прошёл капчу
    is_captcha_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Версия для оптимистичной блокировки: инкрементируется при каждом UPDATE
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
