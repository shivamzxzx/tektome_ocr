import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tektome_ocr.settings")
app = Celery("tektome_ocr")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
