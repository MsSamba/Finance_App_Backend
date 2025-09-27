import os
from celery import Celery

# Set default Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

app = Celery("backend")

# Load custom config from settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks.py files in installed apps
app.autodiscover_tasks()
