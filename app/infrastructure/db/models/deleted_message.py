from datetime import datetime

from sqlalchemy import BigInteger, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class DeletedMessageORM(Base):
    __tablename__ = 'deleted_message'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    # message_id в Telegram
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    text: Mapped[str] = mapped_column(String(4096), nullable=True)
    # Причина удаления: 'captcha_expired' или 'spam_during_captcha'
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
