from datetime import datetime

from django.db import models, transaction

from base.apps.operation.models.movement import Movement
from base.apps.storage.models.cooling_unit import CoolingUnit
from base.apps.storage.models.pricing import Pricing
from base.utils.currencies import quantitize_float

# Constants
MINIMUM_WEIGHT_DIVISOR = 1
MINIMUM_STORAGE_DAYS = 1
ERROR_CHECKOUT_EXCEEDS_INITIAL_WEIGHT = (
    "Cannot checkout more than crate's initial weight"
)
ERROR_CHECKOUT_EXCEEDS_CURRENT_WEIGHT = (
    "Cannot checkout more than 100% of current's crate state"
)
ERROR_CHECKOUT_INSTANCE_REQUIRED = (
    "Please provide a Checkout instance to tie this checkout with"
)


def zero_time_fields(dt):
    """Utility function to zero out time fields from datetime."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)

def get_total_in_cooling_fees(crate, storage_duration_days=None, **kwargs):
    from base.apps.storage.models.cooling_unit_crop import CoolingUnitCrop

    # Get the daily rate from CoolingUnitCrop for the crate's cooling unit and crop
    try:
        cup_crop = CoolingUnitCrop.objects.get(
            cooling_unit=crate.cooling_unit, crop=crate.produce.crop
        )
    except CoolingUnitCrop.DoesNotExist:
        raise ValueError(
            f"No pricing found for cooling unit {crate.cooling_unit.id} and crop {crate.produce.crop.id}"
        )

    metric_multiplier = (
        crate.initial_weight
        if crate.cooling_unit.metric == CoolingUnit.CoolingUnitMetric.KILOGRAMS
        else MINIMUM_WEIGHT_DIVISOR
    )

    # Calculate the storage duration (days) based on checkin and check_out (if available)
    if not storage_duration_days:
        storage_duration_days = get_storage_duration_days(crate, **kwargs)

    # Calculate the cooling fees if we have a valid daily rate and storage duration
    if cup_crop.pricing.pricing_type == Pricing.PricingType.FIXED:
        return quantitize_float(
            metric_multiplier * cup_crop.pricing.fixed_rate, crate.currency
        )
    elif cup_crop.pricing.pricing_type == Pricing.PricingType.PERIODICITY:
        return quantitize_float(
            metric_multiplier * storage_duration_days * cup_crop.pricing.daily_rate,
            crate.currency,
        )

    return 0


@transaction.atomic
def create_partial_checkout(
    crate, weight_in_kg, checkout=None, cooling_fees=None, compute_dependencies=True
):
    from base.apps.storage.models.crate_partial_checkout import CratePartialCheckout

    percentage = weight_in_kg / max(MINIMUM_WEIGHT_DIVISOR, crate.initial_weight)
    percentage_towards_state = weight_in_kg / max(MINIMUM_WEIGHT_DIVISOR, crate.weight)

    if percentage > 1.0:
        raise ValueError(ERROR_CHECKOUT_EXCEEDS_INITIAL_WEIGHT)

    if percentage_towards_state > 1.0:
        raise ValueError(ERROR_CHECKOUT_EXCEEDS_CURRENT_WEIGHT)

    if not checkout:
        raise ValueError(ERROR_CHECKOUT_INSTANCE_REQUIRED)

    if cooling_fees is None:
        cooling_fees = get_total_due_in_cooling_fees(crate) * percentage_towards_state

    # Checkout part or entire crate based on this item
    checkout_item = CratePartialCheckout.objects.create(
        checkout=checkout,
        crate=crate,
        percentage=percentage,
        weight_in_kg=weight_in_kg,
        cooling_fees=cooling_fees,
    )

    crate.weight -= weight_in_kg

    if compute_dependencies:
        crate.compute(save=True)
        checkout.compute(save=True)

    return checkout_item


def get_storage_duration_days(crate, checkout_date=None, checkin_date=None):
    current_datetime = zero_time_fields(datetime.now())

    if crate.produce and crate.produce.checkin:
        if not checkout_date and crate.partial_checkouts.exists():
            checkout_date = zero_time_fields(
                crate.partial_checkouts.last().checkout.movement.date.replace(
                    tzinfo=None
                )
            )

        if not checkin_date and crate.produce.checkin.movement:
            movement = crate.produce.checkin.movement

            checkin_date = zero_time_fields(movement.date.replace(tzinfo=None))

    if not checkout_date:
        checkout_date = current_datetime

    if not checkin_date:
        checkin_date = checkout_date

    # Some of the checkins actually happened before the actual checkout due to the logic removed in this commit
    # So we're comparing if its on the same day, and considering same day even if the checkin_date is after the checkout_date
    is_same_day = (
        checkin_date > checkout_date or checkin_date.date() == checkout_date.date()
    )
    is_marketplace_originated_crate = str(
        crate.produce and crate.produce.checkin.movement.initiated_for
    ) == str(Movement.InitiatedFor.MARKETPLACE_ORDER)

    # Calculate the storage duration (days) based on checkin and check_out
    # Note: Theres an exception for crates that are created through marketplace order movements, that are checked out within the same day
    return (
        0
        if is_marketplace_originated_crate and is_same_day
        else max(MINIMUM_STORAGE_DAYS, (checkout_date - checkin_date).days)
    )


def get_total_paid_in_cooling_fees(crate, **kwargs):
    total_paid_in_cooling_fees = crate.partial_checkouts.aggregate(
        total_paid_in_cooling_fees=models.Sum("cooling_fees")
    )["total_paid_in_cooling_fees"]

    return total_paid_in_cooling_fees or 0


def get_total_due_in_cooling_fees(crate, **kwargs):
    total_amount_in_cooling_fees = get_total_in_cooling_fees(crate, **kwargs)
    total_amount_paid_in_cooling_fees = get_total_paid_in_cooling_fees(crate, **kwargs)

    # Don't allow negative amounts
    fees = max(0, total_amount_in_cooling_fees - total_amount_paid_in_cooling_fees)

    return max(0, quantitize_float(fees, crate.currency))


def get_total_due_in_cooling_fees_per_kg(crate, **kwargs):
    total_due_in_cooling_fees_per_kg = get_total_due_in_cooling_fees(
        crate, **kwargs
    ) / max(MINIMUM_WEIGHT_DIVISOR, crate.weight)

    return max(0, quantitize_float(total_due_in_cooling_fees_per_kg, crate.currency))


def crates_locked_within_marketplace_pending_orders(crate_ids):
    from base.apps.marketplace.models.market_listed_crate import MarketListedCrate

    return MarketListedCrate.objects.filter(
        crate_id__in=crate_ids,
        delisted_at__isnull=True,
        cmp_weight_locked_in_payment_pending_orders_in_kg__gt=0,
    ).exists()
