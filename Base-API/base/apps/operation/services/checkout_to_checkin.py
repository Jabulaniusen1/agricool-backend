from datetime import date
from django.core.exceptions import ValidationError

from base.apps.operation.models import Checkin, Movement, Checkout
from base.apps.storage.models import CoolingUnit, CoolingUnitCrop, Crate, Produce, Crop
from base.apps.user.models import Operator


def convert_checkout_to_checkin(
    *,
    checkout_code,
    owned_by_user_id,
    cooling_unit_id,
    days=None,
    tags=None,
    operator_user_id=None,
):
    """
    Convert a full Checkout into a new Checkin.

    Always re-checkins *all* crates from the checkout (grouped by Produce),
    using the provided cooling_unit_id and owned_by_user_id.

    Returns the created Checkin instance.
    """
    tags = tags or []

    # Find the source checkout
    checkout = Checkout.objects.get(movement__code=checkout_code)
    crates = Crate.objects.filter(partial_checkouts__checkout_id=checkout.id)

    # Determine operator and cooling unit
    operator = Operator.objects.get(user_id=operator_user_id)
    cooling_unit = CoolingUnit.objects.get(id=cooling_unit_id)

    # Create new Movement
    movement = Movement.objects.create(
        code=Movement.generate_code(),
        date=date.today(),
        operator=operator,
        initiated_for=Movement.InitiatedFor.CHECK_IN,
    )

    # Create Checkin
    checkin = Checkin.objects.create(
        owned_by_user_id=owned_by_user_id,
        movement=movement,
    )

    # Create new Produce / Crates
    produces_seen = set()

    for crate in crates:
        if crate.produce.id not in produces_seen:
            produces_seen.add(crate.produce.id)

            # Recreate produce
            old_produce = crate.produce
            crop = Crop.objects.get(id=old_produce.crop.id)

            new_produce = Produce.objects.create(
                harvest_date=old_produce.harvest_date,
                initial_grade=old_produce.initial_grade,
                size=old_produce.size,
                crop=crop,
                checkin=checkin,
            )

        # Pricing logic
        cup_crop = CoolingUnitCrop.objects.filter(
            cooling_unit_id=cooling_unit_id,
            crop=crop,
            active=True,
        ).first()

        if not cup_crop:
            raise ValidationError("This cooling unit doesn't accept this type of produce")

        metric_multiplier = crate.weight if cooling_unit.metric == "KILOGRAMS" else 1

        if cup_crop.pricing.pricing_type == "FIXED":
            price = metric_multiplier * cup_crop.pricing.fixed_rate
        elif days and int(days) > 0 and cup_crop.pricing.pricing_type == "PERIODICITY":
            price = metric_multiplier * int(days) * cup_crop.pricing.daily_rate
        else:
            price = 0

        # Take the last partial checkout weight (or initial weight)
        last_pc = crate.partial_checkouts.latest("id")
        weight = last_pc.weight_in_kg if last_pc else crate.initial_weight

        # Tag (same index-based logic)
        idx = list(crates).index(crate)
        tag_value = tags[idx] if idx < len(tags) else None

        Crate.objects.create(
            produce=new_produce,
            cooling_unit=cooling_unit,
            price_per_crate_per_pricing_type=price,
            currency=crate.currency,
            planned_days=days,
            tag=tag_value,
            weight=weight,
            initial_weight=weight,
            remaining_shelf_life=crate.remaining_shelf_life,
            quality_dt=crate.quality_dt,
            temperature_dt=crate.temperature_dt,
            modified_dt=crate.modified_dt,
        )

    # Mark the original movement as used
    checkout.movement.used_for_checkin = True
    checkout.movement.save()

    # Recompute cooling unit
    cooling_unit.compute(save=True)

    return checkin
