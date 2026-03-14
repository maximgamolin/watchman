from celery import Celery

from app.infrastructure.config import settings

celery_app = Celery(
    'watchman',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['app.infrastructure.celery.tasks'],
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'cleanup-expired-captchas': {
            'task': 'app.infrastructure.celery.tasks.cleanup_expired_captchas',
            # Запускаем каждые 10 секунд
            'schedule': 10.0,
        },
    },
)
