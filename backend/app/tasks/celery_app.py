from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "sync_tasks",
    broker=settings.get_rabbitmq_url(),
    backend=settings.get_redis_url(),
    include=["app.tasks.sync_tasks"]
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
)

# Automated schedules matching Section 20
celery_app.conf.beat_schedule = {
    "sync-all-active-suppliers-every-15-mins": {
        "task": "app.tasks.sync_tasks.sync_all_suppliers_task",
        "schedule": crontab(minute="*/15"),
    },
    "out-of-stock-monitoring-every-10-mins": {
        "task": "app.tasks.sync_tasks.out_of_stock_monitor_task",
        "schedule": crontab(minute="*/10"),
    },
    "catalog-reconcile-daily-at-2am": {
        "task": "app.tasks.sync_tasks.catalog_reconcile_task",
        "schedule": crontab(minute=0, hour=2),
    },
}
