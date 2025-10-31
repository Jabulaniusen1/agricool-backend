from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import transaction

from base.apps.operation.models import Checkin
from base.apps.storage.models import (
    CoolingUnit,
    CoolingUnitCrop,
    Crate,
    Crop,
    Pricing,
    Produce,
)
from base.apps.storage.services.ttpu import compute_initial_ttpu_checkin
from base.apps.user.models import (
    Farmer,
    FarmerSurvey,
    FarmerSurveyCommodity,
    Notification,
    ServiceProvider,
)

# Constants
ERROR_CHECKIN_NOT_EDITABLE = "Check in is not editable."


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
        try:
            crop = Crop.objects.get(id=produce_data["crop"]["id"])
        except Crop.DoesNotExist:
            raise ValidationError(
                f"Crop with ID {produce_data['crop']['id']} not found"
            )

        # Remove fields we handle manually
        produce_data.pop("crop")
        has_picture = produce_data.pop("has_picture", False)

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
            try:
                cooling_unit = CoolingUnit.objects.get(id=crate_data["cooling_unit_id"])
            except CoolingUnit.DoesNotExist:
                raise ValidationError(
                    f"Cooling unit with ID {crate_data['cooling_unit_id']} not found"
                )
            metric_multiplier = (
                crate_data["weight"]
                if cooling_unit.metric == CoolingUnit.CoolingUnitMetric.KILOGRAMS
                else 1
            )

            try:
                cu_crop = CoolingUnitCrop.objects.get(
                    cooling_unit=cooling_unit,
                    crop=crop,
                )
            except CoolingUnitCrop.DoesNotExist:
                raise ValidationError(
                    f"Cooling unit {cooling_unit.id} does not accept crop {crop.id}"
                )

            # Create crate with basic info first
            crate = Crate.objects.create(
                produce=produce_instance,
                cooling_unit=cooling_unit,
                initial_weight=crate_data["weight"],
                weight=crate_data["weight"],
                currency=company.currency,
                planned_days=crate_data.get("planned_days"),
            )

            # Calculate accurate pricing using the compute method
            # This ensures both FIXED and PERIODICITY pricing are calculated correctly
            # PERIODICITY will charge for minimum 1 day on checkin (unless marketplace same-day)
            crate.compute(save=True, compute_dependencies=False)

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
                event_type=Notification.NotificationType.FARMER_SURVEY,
            )
            Notification.objects.create(
                user=operator.user,
                specific_id=produce_instance.id,
                event_type=Notification.NotificationType.FARMER_SURVEY,
            )

    # Handle DTs and TTPU
    if produces_for_DT:
        Crate.objects.filter(produce__in=produces_for_DT).update(run_dt=True)
        for produce in produces_for_DT:
            compute_initial_ttpu_checkin(produce.id, produce.crates.first().id)


def update_checkin(checkin_id, payload):
    """
    Update a checkin (owner / crop / planned_days), if editable,
    and notify related service providers.

    payload can contain: farmer_id, crop_id, planned_days
    """

    try:
        checkin = Checkin.objects.select_related("movement").get(id=checkin_id)
    except Checkin.DoesNotExist:
        raise ValidationError(f"Checkin with ID {checkin_id} not found")
    try:
        produce = Produce.objects.get(checkin_id=checkin_id)
    except Produce.DoesNotExist:
        raise ValidationError(f"No produce found for checkin {checkin_id}")

    # pick any crate attached to the produce (we just need cooling_unit + movement check)
    crate_example = Crate.objects.filter(produce=produce).first()
    cooling_unit = crate_example.cooling_unit
    movement_date = checkin.movement.date

    editable = (
        cooling_unit.editable_checkins
        and movement_date.date() == datetime.today().date()
    )
    if not editable:
        raise ValidationError(ERROR_CHECKIN_NOT_EDITABLE)

    # Update owner
    if payload.get("farmer_id"):
        try:
            farmer = Farmer.objects.get(id=payload["farmer_id"])
        except Farmer.DoesNotExist:
            raise ValidationError(f"Farmer with ID {payload['farmer_id']} not found")
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
    service_providers = ServiceProvider.objects.select_related("user").filter(
        company=cooling_unit.location.company
    )
    for sp in service_providers:
        Notification.objects.create(
            user=sp.user,
            specific_id=checkin.id,
            event_type=Notification.NotificationType.CHECKIN_EDITED,
        )

    return checkin
