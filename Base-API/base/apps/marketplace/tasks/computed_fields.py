from django.db.models import Q
from django.utils import timezone

from base.apps.marketplace.models import MarketListedCrate
from base.celery import app

# Time constants
DAY_START_HOUR = 0
DAY_START_MINUTE = 0
DAY_START_SECOND = 0
DAY_START_MICROSECOND = 0

# Log message templates
RECOMPUTE_SUCCESS_MESSAGE = "Recomputed fields for listing ID {listing_id}."
RECOMPUTE_ERROR_MESSAGE = "Error recomputing fields for listing ID {listing_id}: {error}"


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
    today_start = timezone.now().replace(
        hour=DAY_START_HOUR,
        minute=DAY_START_MINUTE,
        second=DAY_START_SECOND,
        microsecond=DAY_START_MICROSECOND
    )

    # Retrieve active market listings that need recomputation:
    listings = MarketListedCrate.objects.filter(
        Q(delisted_at__isnull=True) &
        (Q(cmp_last_updated_at__isnull=True) | Q(cmp_last_updated_at__lt=today_start))
    )

    # Process each listing individually
    for listing in listings.iterator():
        try:
            listing.compute()
            print(RECOMPUTE_SUCCESS_MESSAGE.format(listing_id=listing.id))
        except Exception as e:
            print(RECOMPUTE_ERROR_MESSAGE.format(listing_id=listing.id, error=e))
