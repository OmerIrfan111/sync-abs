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
    # A hung network call (e.g. a DNS resolution that doesn't respect
    # urllib's own timeout= parameter, observed in practice against real
    # supplier APIs) can otherwise block a worker slot indefinitely with no
    # error ever logged. soft_time_limit raises inside the task first (so
    # cleanup/logging can still run); time_limit force-kills the worker
    # process outright if it doesn't exit within the grace period.
    #
    # Measured in production against real Ingram Micro/D&H catalogs: a full
    # paginated sync routinely takes 540-610s. The limit below gives ~2x
    # headroom over that observed worst case, so it only fires on a genuine
    # hang, never on a legitimately slow-but-successful sync.
    task_soft_time_limit=1200,  # 20 minutes
    task_time_limit=1320,       # 22 minutes
)

# Automated schedules — near real-time sync (every 5 minutes)
celery_app.conf.beat_schedule = {
    "sync-all-active-suppliers-every-5-mins": {
        "task": "app.tasks.sync_tasks.sync_all_suppliers_task",
        "schedule": crontab(minute="*/5"),
    },
    "out-of-stock-monitoring-every-5-mins": {
        "task": "app.tasks.sync_tasks.out_of_stock_monitor_task",
        "schedule": crontab(minute="*/5"),
    },
    "catalog-reconcile-daily-at-2am": {
        "task": "app.tasks.sync_tasks.catalog_reconcile_task",
        "schedule": crontab(minute=0, hour=2),
    },
    "order-ingestion-every-2-mins": {
        "task": "app.tasks.sync_tasks.order_ingestion_task",
        "schedule": crontab(minute="*/2"),
    },
    "tracking-sync-every-10-mins": {
        "task": "app.tasks.sync_tasks.tracking_sync_task",
        "schedule": crontab(minute="*/10"),
    },
}
