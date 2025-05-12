# myproject/celery.py
import os
from celery import Celery
import redis
from datetime import datetime, timedelta
import logging
import django

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('AI-Marketer')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# django.setup()
