from datetime import datetime, timedelta
from django.db.models import Case, F, OuterRef, Q, Subquery, When
from django.utils import timezone

from base.apps.operation.services.checkout import create_partial_checkout
from base.apps.user.models import Notification
from base.celery import app
from base.utils.currencies import quantitize_float

# Currency constants
SUPPORTED_CURRENCY = "NGN"

# Payment constants
DEFAULT_DISCOUNT_AMOUNT = 0.0
MINIMUM_ORDER_AMOUNT = 100

# Movement code templates
MOVEMENT_CODE_TEMPLATE = "MO-#{order_id}-CU-#{cooling_unit_id}"
PRODUCE_IDENTIFIER_TEMPLATE = "MO-#{order_id}-PI-#{produce_id}"

# Celery task names
SMS_NOTIFICATION_TASK = "base.apps.marketplace.tasks.sms.send_sms_notification_to_owner_on_order_completed"

# Error messages
ERROR_UNSUPPORTED_CURRENCY = "Only NGN currency is supported"
ERROR_INVALID_ORDER_STATUS = "Invalid order status"
ERROR_ORDER_AMOUNT_TOO_LOW = "Order total amount should be greater than 100"
ERROR_ORDER_AMOUNT_CHANGED = "Order total amount changed during computation"
ERROR_PICKUP_DETAILS_MISMATCH = "Number of pickup details does not match number of cooling units"
ERROR_MISSING_PICKUP_DETAILS = "Missing pickup details for cooling unit {cu_id}"
ERROR_COOLING_UNIT_NOT_FOUND = "Cooling unit with ID {cu_id} not found"

# Date constants
EPOCH_START = datetime(1970, 1, 1, tzinfo=timezone.utc)
RECOMPUTE_THRESHOLD_DAYS = 1

# Division safety constants
MIN_DIVISOR = 1


"""
Note:
We have extracted complex business logic into dedicated service functions (located in base.apps.marketplace.services.order_services)
to avoid fat models. Fat models can become difficult to maintain, test, and evolve over time.
By moving the business logic to a separate service layer, we keep our models thin and focused on representing data,
while the service layer handles the intricate operational logic. This separation improves code readability and
maintainability.
"""

def process_coupon_code(order, coupon_code):
    """
    Applies a valid coupon code to eligible order items.
    """
    from base.apps.marketplace.models.coupon import Coupon
    from base.apps.marketplace.models.order_crate_item import OrderCrateItem

    selector = OrderCrateItem.objects.annotate(
        new_valid_coupon_id=Subquery(
            Coupon.objects.filter(
                Q(code=coupon_code) &
                Q(revoked_at__isnull=True) &
                (
                    (Q(owned_by_user_id=OuterRef('market_listed_crate__crate__produce__checkin__owned_by_user_id')) &
                     Q(owned_on_behalf_of_company_id__isnull=True)) |
                    Q(owned_on_behalf_of_company_id=OuterRef('market_listed_crate__crate__produce__checkin__owned_on_behalf_of_company_id'))
                )
            ).values('id')[:1]
        )
    ).filter(
        order_id=order.id,
        new_valid_coupon_id__isnull=False,
    ).values('id', 'new_valid_coupon_id')

    OrderCrateItem.objects.filter(
        id__in=selector.values('id'),
    ).update(
        coupon_id=selector.values('new_valid_coupon_id')[:1]
    )


def clear_coupon_code_service(order, coupon_code):
    """
    Clears the coupon code from eligible order items.
    """
    from base.apps.marketplace.models.coupon import Coupon

    item_valid_coupon_query = order.items.annotate(
        matching_coupon_id=Subquery(
            Coupon.objects.filter(
                Q(code=coupon_code) &
                Q(revoked_at__isnull=True) &
                (
                    (Q(owned_by_user_id=OuterRef('market_listed_crate__crate__produce__checkin__owned_by_user_id')) &
                     Q(owned_on_behalf_of_company_id__isnull=True)) |
                    Q(owned_on_behalf_of_company_id=OuterRef('market_listed_crate__crate__produce__checkin__owned_on_behalf_of_company_id'))
                )
            ).values('id')[:1]
        )
    )

    order.items.update(
        coupon_id=Case(
            When(
                coupon_id=Subquery(
                    item_valid_coupon_query.filter(id=OuterRef('id')).values('matching_coupon_id')[:1]
                ),
                then=None
            ),
            default=F('coupon_id')
        )
    )


def process_order_completion(order, payment_through=None, payment_gateway=None, payment_method=None):
    """
    Completes a payment pending order by processing movements, checkouts,
    checkins, crate allocations, notifications, and SMS notifications.
    """
    from base.apps.operation.models import Checkin, Checkout, Movement
    from base.apps.storage.models import CoolingUnit, Crate, Produce

    # Caches to avoid repeated database queries
    cached_cooling_units = {}
    cached_movements = {}
    cached_checkouts = {}
    cached_checkins = {}
    cached_post_produces = {}
    cached_cu_notifications = {}
    listings_to_be_computed = []
    latest_allocated_crates = {}

    items = order.items.all().annotate(
        cooling_unit_id=F('market_listed_crate__crate__cooling_unit_id')
    )

    for item in items.iterator():
        code = MOVEMENT_CODE_TEMPLATE.format(order_id=order.id, cooling_unit_id=item.cooling_unit_id)

        # Retrieve or create CoolingUnit, Movement, Checkout, Checkin
        if code not in cached_cooling_units:
            try:
                cached_cooling_units[code] = CoolingUnit.objects.get(id=item.cooling_unit_id)
            except CoolingUnit.DoesNotExist:
                raise ValueError(ERROR_COOLING_UNIT_NOT_FOUND.format(cu_id=item.cooling_unit_id))
        cooling_unit = cached_cooling_units[code]

        if code not in cached_movements:
            cached_movements[code] = Movement.objects.create(
                date=order.created_at,
                order=order,
                code=code,
                initiated_for=Movement.InitiatedFor.MARKETPLACE_ORDER,
            )
        movement = cached_movements[code]

        if code not in cached_checkouts:
            cached_checkouts[code] = Checkout.objects.create(
                movement=movement,
                paid=True,
                discount_amount=DEFAULT_DISCOUNT_AMOUNT,
                payment_through=payment_through or Checkout.PaymentThrough.DIRECT,
                payment_gateway=payment_gateway,
                payment_method=payment_method or Checkout.PaymentMethod.CASH,
            )
        checkout = cached_checkouts[code]

        if code not in cached_checkins:
            cached_checkins[code] = Checkin.objects.create(
                movement=movement,
                owned_by_user=order.created_by_user,
                owned_on_behalf_of_company=order.owned_on_behalf_of_company,
            )
        checkin = cached_checkins[code]

        # Send notification once per cooling unit
        if code not in cached_cu_notifications:
            cached_cu_notifications[code] = Notification.notify_cooling_unit_operators(
                cooling_unit=cooling_unit,
                specific_id=movement.id,
                event_type=Notification.NotificationType.ORDER_REQUIRES_MOVEMENT,
            )

        market_listed_crate = item.market_listed_crate
        crate = market_listed_crate.crate
        produce = crate.produce

        # Check if ordering an entire crate
        ordered_entire_crate = item.ordered_produce_weight == crate.weight

        checkout_item = create_partial_checkout(
            crate=crate,
            weight_in_kg=item.ordered_produce_weight,
            checkout=checkout,
            cooling_fees=item.cmp_cooling_fees_amount
        )

        produce_common_identifier = PRODUCE_IDENTIFIER_TEMPLATE.format(order_id=order.id, produce_id=produce.id)
        if produce_common_identifier not in cached_post_produces:
            cached_post_produces[produce_common_identifier] = Produce.objects.create(
                crop=produce.crop,
                harvest_date=produce.harvest_date,
                additional_info=produce.additional_info,
                initial_grade=produce.initial_grade,
                size=produce.size,
                checkin=checkin,
            )

        remaining_kg = checkout_item.weight_in_kg
        max_capacity = cooling_unit.crate_weight

        if ordered_entire_crate and remaining_kg == max_capacity:
            latest_crate = Crate.objects.create(
                produce=cached_post_produces[produce_common_identifier],
                initial_weight=remaining_kg,
                weight=remaining_kg,
                planned_days=0,
                cooling_unit=cooling_unit,
                currency=crate.currency,
                price_per_crate_per_pricing_type=crate.price_per_crate_per_pricing_type,
                remaining_shelf_life=crate.remaining_shelf_life,
                run_dt=crate.run_dt,
                quality_dt=crate.quality_dt,
                temperature_dt=crate.temperature_dt,
                modified_dt=crate.modified_dt,
            )
            item.resulting_crates.add(latest_crate)
        else:
            while remaining_kg > 0:
                latest_crate = latest_allocated_crates.get(crate.cooling_unit_id, {}).get(produce.crop.id)
                if latest_crate is None or latest_crate.weight >= max_capacity:
                    # Use the crate with the lowest ttpu (or fall back to the original crate)
                    related_crate = (
                        latest_crate
                        if latest_crate and latest_crate.remaining_shelf_life and crate.remaining_shelf_life and
                        latest_crate.remaining_shelf_life < crate.remaining_shelf_life
                        else crate
                    )
                    latest_crate = Crate.objects.create(
                        produce=cached_post_produces[produce_common_identifier],
                        initial_weight=0,
                        weight=0,
                        planned_days=0,
                        cooling_unit=cooling_unit,
                        currency=crate.currency,
                        price_per_crate_per_pricing_type=crate.price_per_crate_per_pricing_type,
                        remaining_shelf_life=related_crate.remaining_shelf_life,
                        run_dt=related_crate.run_dt,
                        quality_dt=related_crate.quality_dt,
                        temperature_dt=related_crate.temperature_dt,
                        modified_dt=related_crate.modified_dt,
                    )
                    latest_allocated_crates.setdefault(crate.cooling_unit_id, {})[produce.crop.id] = latest_crate

                allocate_amount = min(remaining_kg, max_capacity - latest_crate.weight)
                latest_crate.weight += allocate_amount
                latest_crate.initial_weight += allocate_amount
                latest_crate.save()
                remaining_kg -= allocate_amount

                if not item.resulting_crates.filter(id=latest_crate.id).exists():
                    item.resulting_crates.add(latest_crate)

        listings_to_be_computed.append((market_listed_crate, ordered_entire_crate))

    order.status = order.Status.PAID
    order.status_changed_at = timezone.now()
    order.paid_at = timezone.now()
    order.save()

    # Recompute market listing crates after order completion
    for market_listed_crate, ordered_entire_crate in listings_to_be_computed:
        if market_listed_crate.delisted_at is None:
            if ordered_entire_crate:
                market_listed_crate.delisted_at = timezone.now()
            market_listed_crate.compute(save=True)

    # Send SMS notifications to sellers
    owned_by_users_ids = order.items.values_list(
        'market_listed_crate__crate__produce__checkin__owned_by_user', flat=True
    ).distinct()
    for user_id in owned_by_users_ids:
        app.send_task(
            SMS_NOTIFICATION_TASK,
            args=[order.id, user_id]
        )


def validate_order_payment_conditions(order):
    """
    Validates whether an order is eligible to proceed to payment.
    Checks supported currency, order status, total amounts, and pickup details.
    Raises an Exception if any check fails.
    """
    from base.apps.marketplace.models.order_pickup_details import \
        OrderPickupDetails

    if order.currency != SUPPORTED_CURRENCY:
        raise Exception(ERROR_UNSUPPORTED_CURRENCY)

    if order.status not in [order.Status.CART, order.Status.PAYMENT_PENDING]:
        raise Exception(ERROR_INVALID_ORDER_STATUS)

    if order.currency == SUPPORTED_CURRENCY and (order.cmp_total_produce_amount + order.cmp_total_cooling_fees_amount) < MINIMUM_ORDER_AMOUNT:
        raise Exception(ERROR_ORDER_AMOUNT_TOO_LOW)

    pre_compute_total = order.cmp_total_amount
    order.compute(save=True, compute_dependencies=True)
    post_compute_total = order.cmp_total_amount
    if pre_compute_total != post_compute_total:
        raise Exception(ERROR_ORDER_AMOUNT_CHANGED)

    cooling_units = order.get_cooling_unit_ids()
    order_pickup_details = OrderPickupDetails.objects.filter(order=order)
    if len(order_pickup_details) != len(cooling_units):
        raise Exception(ERROR_PICKUP_DETAILS_MISMATCH)

    pickup_cu_ids = [detail.cooling_unit_id for detail in order_pickup_details]
    for cu_id in cooling_units:
        if cu_id not in pickup_cu_ids:
            raise Exception(ERROR_MISSING_PICKUP_DETAILS.format(cu_id=cu_id))

def compute_order_crate_item(order_crate_item, compute_dependencies=True):
    """
    Computes pricing details for the given order crate item and returns a dictionary
    of computed values.
    
    Args:
        order_crate_item: An instance of OrderCrateItem.
        compute_dependencies (bool): Flag to force recomputation of dependent fields
            (e.g., on the associated MarketListedCrate).

    Returns:
        A dict with keys:
            - ordered_produce_weight (possibly adjusted)
            - frozen_produce_price_per_kg
            - frozen_crate_available_weight
            - ordered_entire_crate (bool)
            - cmp_last_updated_at
            - cmp_produce_amount
            - cmp_discount_amount
            - cmp_cooling_fees_amount
            - cmp_total_amount
    """
    market_listed_crate = order_crate_item.market_listed_crate
    currency = order_crate_item.order.currency

    # Check if the market listed crate needs to be recomputed.
    if compute_dependencies or not market_listed_crate.cmp_last_updated_at:
        comparison_updated_at = order_crate_item.order.cmp_last_updated_at or EPOCH_START
        if (market_listed_crate.cmp_last_updated_at < comparison_updated_at or
            (market_listed_crate.cmp_last_updated_at - comparison_updated_at) > timedelta(days=RECOMPUTE_THRESHOLD_DAYS)):
            market_listed_crate.compute(save=True)

    # Retrieve the latest produce price per kg.
    latest_price_obj = market_listed_crate.prices.order_by('-created_at').first()
    produce_price_per_kg = latest_price_obj.produce_price_per_kg if latest_price_obj else 0

    # Use computed available weight or fallback to the crate's weight.
    crate_available_weight = market_listed_crate.cmp_available_weight_in_kg or market_listed_crate.crate.weight

    # Calculate cooling fee per kg, ensuring no division by zero.
    cooling_fee_per_kg = quantitize_float(
        market_listed_crate.cmp_pending_in_cooling_fees / max(MIN_DIVISOR, crate_available_weight),
        currency
    )

    # Adjust the ordered weight if it exceeds available weight.
    ordered_weight = order_crate_item.ordered_produce_weight
    if ordered_weight > crate_available_weight:
        ordered_weight = crate_available_weight

    # Compute amounts.
    produce_amount = quantitize_float(max(ordered_weight * produce_price_per_kg, 0), currency)
    cooling_fees_amount = quantitize_float(max(ordered_weight * cooling_fee_per_kg, 0), currency)

    # Compute discount if a coupon is applied.
    discount_amount = (quantitize_float(produce_amount * order_crate_item.coupon.discount_percentage, currency)
                       if order_crate_item.coupon else 0)

    # Total amount: maximum of net produce amount (after discount) and cooling fees.
    total_amount = quantitize_float(max(produce_amount - discount_amount, cooling_fees_amount, 0), currency)

    return {
        'ordered_produce_weight': ordered_weight,
        'frozen_produce_price_per_kg': produce_price_per_kg,
        'frozen_crate_available_weight': crate_available_weight,
        'ordered_entire_crate': (ordered_weight == crate_available_weight),
        'cmp_last_updated_at': timezone.now(),
        'cmp_produce_amount': produce_amount,
        'cmp_discount_amount': discount_amount,
        'cmp_cooling_fees_amount': cooling_fees_amount,
        'cmp_total_amount': total_amount,
    }