from celery import shared_task
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@shared_task
def test_scheduled_task():
    logger.error("Scheduled task recieved!")
    logger.error(f"Scheduled task ran at: {datetime.now()}")