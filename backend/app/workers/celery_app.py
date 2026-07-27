from celery import Celery
from celery.signals import setup_logging as celery_setup_logging

from app.core.config import settings
from app.core.logging_config import setup_logging

celery = Celery(
    "news_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_hijack_root_logger=False,
    worker_redirect_stdouts=False,
    beat_schedule={
        "fetch-gdelt-every-6-hours": {
            "task": "app.workers.tasks.trigger_gdelt_fetch",
            "schedule": 21600,  # 6 hours
            "options": {
                "expires": 600.0,
            },
        },
        "gdelt-backfill-every-40-minutes": {
            "task": "app.workers.tasks.trigger_gdelt_backfill",
            "schedule": 2400,  # 40 minutes
            "options": {
                "expires": 1200.0,
            },
        },
    },
)


@celery_setup_logging.connect
def config_loggers(*args, **kwargs):
    """Override logging for Celery workers."""
    setup_logging()
