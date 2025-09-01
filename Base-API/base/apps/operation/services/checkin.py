from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import transaction

from base.apps.operation.models import Checkin
from base.apps.storage.models import CoolingUnit, CoolingUnitCrop, Crate, Crop, Produce
from base.apps.storage.services.ttpu import compute_initial_ttpu_checkin
from base.apps.user.models import (
    Farmer,
    FarmerSurvey,
    FarmerSurveyCommodity,
    Notification,
    ServiceProvider,
)


@transaction.atomic
def handle_produces_for_checkin(checkin, produces_payload, operator):
    """
    Creates Produce and Crates for the given checkin and runs
    pricing, DT, notification and TTPU logic.
    """
    company = operator.company
    farmer_survey = FarmerSurvey.objects.filter(
        farmer__user=checkin.owned_by_user
    ).first()

    produces_for_DT = []

    for produce_data in produces_payload:
        crop = Crop.objects.get(id=produce_data["crop"]["id"])

        # Remove fields we handle manually
        produce_data.pop("crop")
        has_picture = produce_data.pop("hasPicture", False)

        crates_data = produce_data.pop("crates")

        # Optional picture value
        picture = None
        if has_picture:
            picture = produce_data.get("picture")

        produce_instance = Produce.objects.create(
            crop=crop,
            checkin=checkin,
            picture=picture,
            **produce_data,
        )

        # Create the crates and calculate price
        for crate_data in crates_data:
            cooling_unit = CoolingUnit.objects.get(id=crate_data["cooling_unit_id"])
            metric_multiplier = (
                crate_data["weight"] if cooling_unit.metric == "KILOGRAMS" else 1
            )

            cu_crop = CoolingUnitCrop.objects.get(
                cooling_unit=cooling_unit,
                crop=crop,
            )
            price = (
                metric_multiplier * cu_crop.pricing.fixed_rate
                if cu_crop.pricing.pricing_type == "FIXED"
                else metric_multiplier * cu_crop.pricing.daily_rate
            )

            crate = Crate.objects.create(
                produce=produce_instance,
                cooling_unit=cooling_unit,
                initial_weight=crate_data["weight"],
                weight=crate_data["weight"],
                price_per_crate_per_pricing_type=price,
                currency=company.currency,
            )

        # DT / FarmerSurvey logic
        if crop.digital_twin_identifier and cooling_unit.location.company.digital_twin:
            produces_for_DT.append(produce_instance)

        needs_notification = (
            not farmer_survey
            or not FarmerSurveyCommodity.objects.filter(
                farmer_survey=farmer_survey.id, crop=crop
            ).exists()
        )

        if needs_notification:
            Notification.objects.create(
                user=checkin.owned_by_user,
                specific_id=produce_instance.id,
                event_type="FARMER_SURVEY",
            )
            Notification.objects.create(
                user=operator.user,
                specific_id=produce_instance.id,
                event_type="FARMER_SURVEY",
            )

    # Handle DTs and TTPU
    if produces_for_DT:
        Crate.objects.filter(produce__in=produces_for_DT).update(runDT=True)
        for produce in produces_for_DT:
            compute_initial_ttpu_checkin(produce.id, produce.crates.first().id)


def update_checkin(checkin_id, payload):
    """
    Update a checkin (owner / crop / planned_days), if editable,
    and notify related service providers.

    payload can contain: farmer_id, crop_id, planned_days
    """

    checkin = Checkin.objects.select_related("movement").get(id=checkin_id)
    produce = Produce.objects.get(checkin_id=checkin_id)

    # pick any crate attached to the produce (we just need cooling_unit + movement check)
    crate_example = Crate.objects.filter(produce=produce).first()
    cooling_unit = crate_example.cooling_unit
    movement_date = checkin.movement.date

    editable = (
        cooling_unit.editable_checkins
        and movement_date.date() == datetime.today().date()
    )
    if not editable:
        raise ValidationError("Check in is not editable.")

    # Update owner
    if payload.get("farmer_id"):
        farmer = Farmer.objects.get(id=payload["farmer_id"])
        checkin.owned_by_user_id = farmer.user_id
        checkin.save()

    # Update crop
    if payload.get("crop_id"):
        produce.crop_id = payload["crop_id"]
        produce.save()

    # Update planned days on all crates related to this produce
    if payload.get("planned_days") is not None:
        Crate.objects.filter(produce=produce).update(
            planned_days=payload["planned_days"]
        )

    # Notify all service providers
    for sp in ServiceProvider.objects.filter(company=cooling_unit.location.company):
        Notification.objects.create(
            user=sp.user,
            specific_id=checkin.id,
            event_type="CHECKIN_EDITED",
        )

    return checkin
