import os
from celery import Celery
from celery.signals import worker_process_init
from app.core.config import settings
from app.core.logging_config import setup_logging

celery = Celery(
    "news_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.workers.tasks']
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

@worker_process_init.connect
def init_worker(**kwargs):
    """Configure logging when each Celery worker process starts."""
    setup_logging()