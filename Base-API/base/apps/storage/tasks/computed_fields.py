from django.db.models import Q
from django.utils import timezone

from base.apps.storage.models import Crate, Produce
from base.celery import app


@app.task
def recompute_computed_fields():

    for crate in Crate.objects.filter(
        # last computed time is older than todays begin of the day
        (Q(cmp_last_updated_at__isnull=True) | Q(cmp_last_updated_at__lt=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)))
    ).iterator():
        try:
            crate.compute(save=True, compute_dependencies=False)
        except:
            # Ignore errors as it will prevent the further items to be computed
            pass

    for produce in Produce.objects.filter(
        # last computed time is older than todays begin of the day
        (Q(cmp_last_updated_at__isnull=True) | Q(cmp_last_updated_at__lt=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)))
    ).iterator():
        try:
            produce.compute(save=True)
        except:
            # Ignore errors as it will prevent the further items to be computed
            pass
