import json
import logging
from datetime import datetime, timezone

import requests

from app.infrastructure.celery.app import celery_app
from app.infrastructure.config import settings
from app.infrastructure.redis.client import get_sync_redis

logger = logging.getLogger(__name__)

# Префикс ключей капчи в Redis
CAPTCHA_KEY_PREFIX = 'captcha:'


def _delete_telegram_message(group_id: int, message_id: int) -> None:
    """Удаляет сообщение через Telegram Bot API (синхронный вызов для Celery)."""
    url = f'https://api.telegram.org/bot{settings.bot_token}/deleteMessage'
    try:
        resp = requests.post(url, json={'chat_id': group_id, 'message_id': message_id}, timeout=10)
        if not resp.ok:
            logger.warning(
                '[tasks._delete_telegram_message] Failed to delete message %s in group %s: %s',
                message_id, group_id, resp.text,
            )
    except Exception as exc:
        logger.error(
            '[tasks._delete_telegram_message] Error deleting message %s in group %s: %s',
            message_id, group_id, str(exc),
        )


def _store_deleted_message_in_db(session, user_id: int, group_id: int, message_id: int,
                                   text: str, reason: str) -> None:
    """Сохраняет запись об удалённом сообщении в базу данных."""
    from app.infrastructure.db.models.deleted_message import DeletedMessageORM
    record = DeletedMessageORM(
        user_id=user_id,
        group_id=group_id,
        message_id=message_id,
        text=text,
        reason=reason,
    )
    session.add(record)
    session.commit()


@celery_app.task(name='app.infrastructure.celery.tasks.cleanup_expired_captchas')
def cleanup_expired_captchas() -> None:
    """
    Периодическая задача (каждые 10 секунд).
    Находит просроченные сессии капчи в Redis, удаляет сообщение бота в группе
    и сохраняет исходное сообщение пользователя в таблицу deleted_message.
    """
    redis_client = get_sync_redis()
    now = datetime.now(timezone.utc)

    logger.debug('[cleanup_expired_captchas] Starting scan for expired captchas')

    expired_keys = []
    for key in redis_client.scan_iter(f'{CAPTCHA_KEY_PREFIX}*'):
        raw = redis_client.get(key)
        if not raw:
            continue

        try:
            session_data = json.loads(raw)
        except json.JSONDecodeError:
            logger.error('[cleanup_expired_captchas] Invalid JSON for key %s', key)
            continue

        created_at = datetime.fromisoformat(session_data['created_at'])
        elapsed = (now - created_at).total_seconds()

        if elapsed >= settings.captcha_ttl_seconds:
            expired_keys.append((key, session_data))

    if not expired_keys:
        logger.debug('[cleanup_expired_captchas] No expired captchas found')
        return

    logger.info('[cleanup_expired_captchas] Found %d expired captcha(s)', len(expired_keys))

    from app.infrastructure.db.sync_session import get_sync_session
    db_session = get_sync_session()

    try:
        for key, session_data in expired_keys:
            user_id = session_data['user_id']
            group_id = session_data['group_id']
            captcha_message_id = session_data['captcha_message_id']
            original_message_id = session_data['original_message_id']
            original_message_text = session_data.get('original_message_text', '')

            logger.info(
                '[cleanup_expired_captchas] Expiring captcha for user %s in group %s',
                user_id, group_id,
            )

            # Удаляем сообщение бота с капчей из группы
            _delete_telegram_message(group_id, captcha_message_id)

            # Удаляем исходное сообщение пользователя из группы
            _delete_telegram_message(group_id, original_message_id)

            # Сохраняем исходное сообщение пользователя в БД
            _store_deleted_message_in_db(
                session=db_session,
                user_id=user_id,
                group_id=group_id,
                message_id=original_message_id,
                text=original_message_text,
                reason='captcha_expired',
            )

            # Удаляем ключ из Redis
            redis_client.delete(key)
            logger.info(
                '[cleanup_expired_captchas] Cleaned up captcha key %s', key,
            )
    except Exception as exc:
        logger.error('[cleanup_expired_captchas] Error during cleanup: %s', str(exc))
        db_session.rollback()
        raise
    finally:
        db_session.close()
