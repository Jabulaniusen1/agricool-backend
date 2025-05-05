from django.db.models import Q
from django.utils import timezone

from base.apps.marketplace.models import MarketListedCrate
from base.celery import app


@app.task
def recompute_computed_fields():
    """
    Recomputes the computed fields for active market listings (MarketListedCrate).

    Filters for listings that are not delisted and whose computed fields have never been set
    or were last updated before the start of the current day. For each listing meeting these
    criteria, the compute() method is called to update computed values.

    Errors are printed (and are captured by Sentry).
    """
    # Determine the start of today (midnight) in the current timezone
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Retrieve active market listings that need recomputation:
    listings = MarketListedCrate.objects.filter(
        Q(delisted_at__isnull=True) &
        (Q(cmp_last_updated_at__isnull=True) | Q(cmp_last_updated_at__lt=today_start))
    )

    # Process each listing individually
    for listing in listings.iterator():
        try:
            listing.compute()
            print(f"Recomputed fields for listing ID {listing.id}.")
        except Exception as e:
            print(f"Error recomputing fields for listing ID {listing.id}: {e}")
