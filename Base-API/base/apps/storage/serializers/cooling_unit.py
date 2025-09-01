import math
from datetime import datetime, timedelta

from django.db.models import Count, Exists, F, OuterRef, Prefetch, Q, Subquery, Sum
from rest_framework import serializers

from base.apps.operation.models import Movement
from base.apps.storage.serializers.operator_assigned_cooling_unit import (
    OperatorAssignedCoolingUnitSerializer,
)
from base.apps.storage.services.cooling_unit_setup import (
    create_cooling_unit_from_payload,
    update_cooling_unit_from_payload,
)

from ..models import CoolingUnit, CoolingUnitSpecifications, Crate, Produce


class CoolingUnitSerializer(serializers.ModelSerializer):
    crops = serializers.SerializerMethodField()
    sensor_list = serializers.SerializerMethodField()
    latest_temperature = serializers.SerializerMethodField()
    latest_temperature_timestamp = serializers.SerializerMethodField()
    commodity_infos = serializers.SerializerMethodField()
    commodity_total = serializers.SerializerMethodField()
    common_pricing_type = serializers.SerializerMethodField()
    sensor_error = serializers.SerializerMethodField()
    last_checkin_date = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    date_operator_assigned = serializers.SerializerMethodField()
    power_options = serializers.SerializerMethodField()

    class Meta:
        model = CoolingUnit
        fields = (
            "id",
            "name",
            "location",
            "metric",
            "sensor",
            "sensor_list",
            "capacity_in_metric_tons",
            "capacity_in_number_crates",
            "occupancy",
            "occupancy_modified_date",
            "date_last_modified",
            "date_creation",
            "date_operator_assigned",
            "cooling_unit_type",
            "crops",
            "room_height",
            "room_length",
            "room_width",
            "room_weight",
            "operators",
            "latest_temperature",
            "crate_weight",
            "crate_width",
            "crate_length",
            "crate_height",
            "commodity_infos",
            "food_capacity_in_metric_tons",
            "public",
            "common_pricing_type",
            "sensor_error",
            "latest_temperature_timestamp",
            "last_checkin_date",
            "can_delete",
            "commodity_total",
            "power_options",
            "editable_checkins",
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.pop("sensor_user_cooling_unit", None)
        return representation

    @staticmethod
    def optimized_init(queryset):
        latest_temperature_subquery = CoolingUnitSpecifications.objects.filter(
            cooling_unit=OuterRef("id"), specification_type="TEMPERATURE"
        ).order_by("-datetime_stamp")

        return CoolingUnitSerializer(
            (
                queryset.select_related(
                    "location",
                    "location__company",
                )
                .prefetch_related(
                    "crop_cooling_unit",
                    "crop_cooling_unit__pricing",
                    "crop_cooling_unit__crop",
                    "sensor_user_cooling_unit",
                    Prefetch(
                        "crate_cooling_unit",
                        queryset=Crate.objects.filter(weight__gt=0),
                    ),
                    "cooling_unit_Power",
                    "date_operator_assigned",
                    "crate_cooling_unit__produce__crop",
                    Prefetch(
                        "crate_cooling_unit__produce__checkin__movement",
                        queryset=Movement.objects.order_by("-date"),
                        to_attr="prefetched_movements",
                    ),
                )
                .annotate(
                    latest_spec_temperature_value=Subquery(
                        latest_temperature_subquery.values("value")[:1]
                    ),
                    latest_spec_temperature_datetime_stamp=Subquery(
                        latest_temperature_subquery.values("datetime_stamp")[:1]
                    ),
                    has_checked_in_produce=Exists(
                        Produce.objects.filter(
                            crates__cooling_unit=OuterRef("id"),
                            crates__in=Crate.generate_checkedin_crates_subquery(),
                        )
                    ),
                )
            ),
            many=True,
        )

    def create(self, validated_data):
        payload = self.context["request"].data
        cooling_unit = create_cooling_unit_from_payload(payload)
        return cooling_unit

    def update(self, instance, validated_data):
        payload = self.context["request"].data
        updated_cu = update_cooling_unit_from_payload(payload, instance.id)
        return updated_cu

    def get_date_operator_assigned(self, instance):
        operators_assigned = instance.date_operator_assigned.all()
        return OperatorAssignedCoolingUnitSerializer(operators_assigned, many=True).data

    def get_crops(self, instance):
        cu_crops = instance.crop_cooling_unit.all()

        return [
            {
                "id": crop.id,
                "crop_id": crop.crop.id,
                "active": crop.active,
                "pricing": (
                    {
                        "id": crop.pricing.id,
                        "pricing_type": crop.pricing.pricing_type,
                        "fixed_rate": crop.pricing.fixed_rate,
                        "daily_rate": crop.pricing.daily_rate,
                    }
                    if crop.pricing
                    else None
                ),
            }
            for crop in cu_crops
        ]

    def _get_latest_spec_temperature(self, instance):
        latest_spec_temperature_value = getattr(
            instance, "latest_spec_temperature_value", False
        )
        latest_spec_temperature_datetime_stamp = getattr(
            instance, "latest_spec_temperature_datetime_stamp", False
        )

        if (
            latest_spec_temperature_value is not False
            and latest_spec_temperature_datetime_stamp is not False
        ):
            return latest_spec_temperature_value, latest_spec_temperature_datetime_stamp

        try:
            latest_spec_temperature = instance.specification_cooling_unit.filter(
                specification_type="TEMPERATURE"
            ).latest("datetime_stamp")

            if latest_spec_temperature:
                return (
                    latest_spec_temperature.value,
                    latest_spec_temperature.datetime_stamp,
                )
        except:
            pass

        return None, None

    def get_latest_temperature(self, instance):
        value, date = self._get_latest_spec_temperature(instance)
        return value if value else None

    def get_latest_temperature_timestamp(self, instance):
        value, date = self._get_latest_spec_temperature(instance)
        return date if date else None

    def get_commodity_infos(self, instance):
        total_weight = (
            instance.crate_cooling_unit.aggregate(total=Sum("weight"))["total"] or 0
        )

        if total_weight == 0:
            return []

        commodity_infos = (
            instance.crate_cooling_unit.filter(weight__gt=0)
            .values(
                crop_name=F("produce__crop__name"),
                optimal_storage_temperature=F(
                    "produce__crop__optimal_storage_temperature"
                ),
            )
            .annotate(
                combined_weight=Sum("weight"),
                crates_number=Count("id"),
            )
        )

        return [
            {
                "commodity": info["crop_name"],
                "percentage": (
                    math.ceil((info["combined_weight"] / total_weight) * 100)
                    if total_weight
                    else 0
                ),
                "combined_weight": float(info["combined_weight"]),
                "crates_number": info["crates_number"],
                "optimal_storage_temperature": info["optimal_storage_temperature"],
            }
            for info in commodity_infos
        ]

    def get_commodity_total(self, instance):
        # Group crates by crop and calculate total weight for each group
        grouped_weights = instance.crate_cooling_unit.values(
            "produce__crop"
        ).annotate(  # Group by crop
            total_weight=Sum("weight")
        )  # Calculate weight for each crop group

        # Calculate the total weight manually from grouped results
        total_weight = sum(group["total_weight"] for group in grouped_weights)

        # Count the total number of crates
        total_crates = instance.crate_cooling_unit.count()

        # Return the results
        return {
            "total_weight": total_weight,
            "total_crates": total_crates,
        }

    def get_common_pricing_type(self, instance):
        filtered_crop = (
            instance.crop_cooling_unit.filter(crop_id__in=[77, 1])
            .order_by("-crop_id")
            .first()
        )

        if not filtered_crop or not filtered_crop.pricing:
            return None

        pricing = filtered_crop.pricing
        pricing_value = (
            pricing.daily_rate
            if pricing.pricing_type == "PERIODICITY"
            else pricing.fixed_rate
        )

        return {
            "type": pricing.pricing_type,
            "value": pricing_value,
            "pricing_id": pricing.id,
            "metric": instance.metric,
        }

    def get_sensor_error(self, instance):
        if not instance.sensor_user_cooling_unit.exists():
            return False

        value, date = self._get_latest_spec_temperature(instance)

        if value is None and date is None:
            return False

        twelve_hours_ago = datetime.now().astimezone() - timedelta(hours=12)
        return date < twelve_hours_ago if date else False

    def get_last_checkin_date(self, instance):
        # Access prefetched movements directly
        prefetched_movements = getattr(instance, "prefetched_movements", None)

        if prefetched_movements:
            # Get the latest date from prefetched movements
            return max(
                (movement.date for movement in prefetched_movements if movement.date),
                default=None,
            )

        # No movements prefetched
        try:
            latest_movement = (
                Movement.objects.filter(
                    checkins__produces__crates__cooling_unit=instance.id
                )
                .distinct()
                .order_by("-date")
                .latest("date")
            )
            return latest_movement.date if latest_movement else None
        except:
            return None

    # Cooling unit can only be deleted if all produces have the status of checkout complete as true
    def get_can_delete(self, instance):
        has_checked_in_produce_annotated = getattr(
            instance, "has_checked_in_produce", None
        )

        if has_checked_in_produce_annotated is not None:
            return not has_checked_in_produce_annotated

        return not Produce.objects.filter(
            Q(crates__cooling_unit=instance)
            & Exists(Crate.generate_checkedin_crates_subquery())
        ).exists()

    def get_sensor_list(self, instance):
        return instance.sensor_user_cooling_unit.values(
            "id",
            "source_id",
            "type",
            "date_sensor_first_linked",
            "username",
        )

    def get_power_options(self, instance):
        return instance.cooling_unit_Power.values()
