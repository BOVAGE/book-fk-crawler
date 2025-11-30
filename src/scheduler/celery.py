import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from celery import Celery
from celery.schedules import crontab

from src.config import settings

app = Celery("my_crawler_app", broker=settings.CELERY_BROKER_URL)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "crawl-every-hour": {
            "task": "scheduler.tasks.execute_crawl",
            "schedule": crontab(minute=19, hour="*"),  # Runs at HH:00 every hour
            # "args": (7,),  # Limit to 7 pages per crawl
        },
        # Daily report generation - runs at 6 AM UTC
        "daily-report": {
            "task": "scheduler.tasks.generate_daily_change_report",
            "schedule": crontab(minute=27, hour=11),
        },
        # "test-crawl": {
        #     "task": "scheduler.tasks.execute_crawl",
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
