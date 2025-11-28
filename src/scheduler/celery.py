import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from celery import Celery
from src.config import settings
from celery.schedules import crontab


app = Celery("my_crawler_app", broker=settings.CELERY_BROKER_URL)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "scrape-every-hour": {
            "task": "scheduler.tasks.execute_scrape",
            "schedule": crontab(minute=0, hour="*"),  # Runs at HH:00 every hour
        },
        # Daily report generation - runs at 6 AM UTC
        "daily-report": {
            "task": "scheduler.tasks.generate_daily_change_report",
            "schedule": crontab(minute=37, hour=3),
        },
        # "test-scrape": {
        #     "task": "scheduler.tasks.execute_scrape",
        #     "schedule": crontab(minute="*/5"),  # Every 5 minutes for testing
        #     "options": {"expires": 60 * 4},  # Task expires after 4 minutes
        # },
        # "test-daily-report": {
        #     "task": "scheduler.tasks.generate_daily_change_report",
        #     "schedule": crontab(minute="*/5"),  # Every 5 minutes for testing
        #     "options": {"expires": 60 * 4},  # Task expires after 4 minutes
        # },
    },
)

app.autodiscover_tasks(["scheduler.tasks"])
