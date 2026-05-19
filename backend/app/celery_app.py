from celery import Celery
from app.config import settings


celery_app = Celery(
    "qa_agent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.documents.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
