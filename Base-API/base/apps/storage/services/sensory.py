import logging

from django.db import transaction
from django.utils import timezone

from base.apps.storage.models import (CoolingUnitSpecifications,
                                      SensorIntegration)
from base.apps.user.models.notification import Notification

from .sensors.utils import build_integration, fetch_ecozen_temperature

logger = logging.getLogger(__name__)

@transaction.atomic
def load_temperature(cooling_unit, specification_type="TEMPERATURE"):
    # Gather credentials
    try:
        credentials = SensorIntegration.objects.filter(cooling_unit=cooling_unit).values()[0]
    except:
        raise Exception(f"Credentials for cooling unit {cooling_unit.id} were not found")

    # Special handling for Ecozen.
    # We are maintaining the previous implementation since we lack valid credentials for testing.
    if credentials["type"] == "ecozen":
        try:
            updated_date, updated_value, updated_point_value = fetch_ecozen_temperature(credentials)
        except Exception as e:
            logger.error(f"Ecozen data retrieval failed: {str(e)}")
            return

    else:
        # Standard integration handling
        integration = build_integration(cooling_unit, credentials)

        if not integration:
            raise Exception(f"No valid integration found for {cooling_unit.id}")

        datums = integration.get_datums_from_source(source_id=credentials.get("source_id"))

        if not datums:
            print(f"No temperature data available for cooling unit {cooling_unit.id}")
            return None

        latest_datum = max(datums, key=lambda d: d.datetime_stamp)
        updated_date = latest_datum.datetime_stamp
        if timezone.is_naive(updated_date):
            updated_date = timezone.make_aware(updated_date)
        updated_value = latest_datum.value
        updated_point_value = None

    # Process and store temperature data
    if CoolingUnitSpecifications.objects.filter(
        cooling_unit=cooling_unit, specification_type="TEMPERATURE"
    ).exists():
        if updated_value:
            CoolingUnitSpecifications.objects.get_or_create(
                datetime_stamp=updated_date,
                specification_type="TEMPERATURE",
                value=updated_value,
                set_point_value=updated_point_value,
                cooling_unit=cooling_unit,
            )

            Notification.objects.filter(event_type="SENSOR_ERROR", specific_id=cooling_unit.id).delete()

        else:
            if not Notification.objects.filter(specific_id=cooling_unit.id, event_type="SENSOR_ERROR").exists():
                Notification.notify_cooling_unit_operators(
                    cooling_unit=cooling_unit,
                    event_type="SENSOR_ERROR",
                    specific_id=cooling_unit.id,
                )
                Notification.notify_cooling_unit_service_providers(
                    cooling_unit=cooling_unit,
                    event_type="SENSOR_ERROR",
                    specific_id=cooling_unit.id,
                )
    else:
        try:
            CoolingUnitSpecifications.objects.create(
                datetime_stamp=updated_date,
                specification_type="TEMPERATURE",
                value=updated_value,
                set_point_value=updated_point_value,
                cooling_unit=cooling_unit,
            )
        except:
            print("Error in setting cooling unit specification")