from django.db.models import Q
from django.utils import timezone

from base.apps.storage.models import Crate, Produce
from base.celery import app

# Time constants
DAY_START_HOUR = 0
DAY_START_MINUTE = 0
DAY_START_SECOND = 0
DAY_START_MICROSECOND = 0


@app.task
def recompute_computed_fields():
    today_start = timezone.now().replace(
        hour=DAY_START_HOUR, 
        minute=DAY_START_MINUTE, 
        second=DAY_START_SECOND, 
        microsecond=DAY_START_MICROSECOND
    )
    
    # Optimize crate queries with select_related
    crates = Crate.objects.select_related(
        'produce', 
        'cooling_unit', 
        'produce__checkin'
    ).filter(
        Q(cmp_last_updated_at__isnull=True) | Q(cmp_last_updated_at__lt=today_start)
    )
    
    for crate in crates.iterator():
        try:
            crate.compute(save=True, compute_dependencies=False)
        except Exception as e:
            # Log specific error instead of ignoring silently
            print(f"Error computing crate {crate.id}: {e}")

    # Optimize produce queries with select_related  
    produces = Produce.objects.select_related(
        'checkin',
        'crop',
        'checkin__owned_by_user'
    ).filter(
        Q(cmp_last_updated_at__isnull=True) | Q(cmp_last_updated_at__lt=today_start)
    )
    
    for produce in produces.iterator():
        try:
            produce.compute(save=True)
        except Exception as e:
            # Log specific error instead of ignoring silently
            print(f"Error computing produce {produce.id}: {e}")
