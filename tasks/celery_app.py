from celery import Celery
from celery.schedules import crontab
from config import settings

celery_app = Celery(
    "price_engine",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks.price_tracker", "tasks.alert_notifier"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

# Scheduled tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Scrape tracked products every hour
    "scrape-tracked-products": {
        "task":     "tasks.price_tracker.scrape_all_tracked",
        "schedule": crontab(minute=0),   # top of every hour
    },
    # Check alerts every hour (30 min offset from scrape)
    "check-price-alerts": {
        "task":     "tasks.alert_notifier.check_and_notify",
        "schedule": crontab(minute=30),  # :30 past every hour
    },
}
