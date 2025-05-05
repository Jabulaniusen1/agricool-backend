import os
from celery import Celery
from base.apps.marketplace.celery import beat_schedule as marketplace_beat_schedule
from base.apps.storage.celery import beat_schedule as storage_beat_schedule
from base.apps.prediction.celery import beat_schedule as prediction_beat_schedule

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")

app = Celery("base")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    **marketplace_beat_schedule,
    **storage_beat_schedule,
    **prediction_beat_schedule,
}
