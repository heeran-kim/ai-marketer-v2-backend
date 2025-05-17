# myproject/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('AI-Marketer')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# django.setup()
