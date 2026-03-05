import os
from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery = Celery(
    "news_worker",
    broker=redis_url,
    backend=redis_url,
    include=['app.workers.tasks']
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)