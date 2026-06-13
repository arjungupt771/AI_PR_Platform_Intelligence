import asyncio
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "pr_platform",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "update-pr-statuses": {
            "task": "app.workers.tasks.sync_open_prs",
            "schedule": crontab(minute="*/15"),
        },
    },
)


def run_async(coro):
    """Helper to run async functions in Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
