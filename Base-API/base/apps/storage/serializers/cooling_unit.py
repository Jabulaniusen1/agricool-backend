import math
from datetime import datetime, timedelta

from django.db.models import (Count, Exists, F, OuterRef, Prefetch, Q, Subquery,
                              Sum)
from rest_framework import serializers

from base.apps.operation.models import Movement
from base.apps.storage.serializers.cooling_unit_power import \
    CoolingUnitPowerSerializer
from base.apps.storage.serializers.operator_assigned_cooling_unit import \
    OperatorAssignedCoolingUnitSerializer
from base.apps.user.models import Country, Operator

from ..models import (CoolingUnit, CoolingUnitCrop, CoolingUnitPower,
                      CoolingUnitSpecifications, Crate, Crop, Location,
                      OperatorAssignedCoolingUnit, Pricing, Produce,
                      SensorIntegration)
from ..services.sensory import load_temperature


def add_power_default_values(power_options):
    # print("initial", power_options)

    if not power_options.get("pv_panel_type"):
        power_options["pv_panel_type"] = None

    if not power_options.get("refrigerant_type"):
        power_options["refrigerant_type"] = "other"
    if not power_options.get("power_source"):
        power_options["power_source"] = "PV_PANELS" # TODO: fix
    if not power_options.get("electricity_storage_system"):
        power_options["electricity_storage_system"] = "none"
    if not power_options.get("thermal_storage_method"):
        power_options["thermal_storage_method"] = "none"

    return power_options

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
            'editable_checkins'
        )


    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.pop('sensor_user_cooling_unit', None)
        return representation

    @staticmethod
    def optimized_init(queryset):
        latest_temperature_subquery = CoolingUnitSpecifications.objects.filter(
            cooling_unit=OuterRef("id"),
            specification_type="TEMPERATURE"
        ).order_by("-datetime_stamp")

        return CoolingUnitSerializer((
            queryset
            .select_related(
                "location",
                "location__company",
            )
            .prefetch_related(
                "crop_cooling_unit",
                "crop_cooling_unit__pricing",
                "crop_cooling_unit__crop",
                "sensor_user_cooling_unit",
                Prefetch("crate_cooling_unit", queryset=Crate.objects.filter(weight__gt=0)),
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
                latest_spec_temperature_value=Subquery(latest_temperature_subquery.values("value")[:1]),
                latest_spec_temperature_datetime_stamp=Subquery(latest_temperature_subquery.values("datetime_stamp")[:1]),
                has_checked_in_produce=Exists(
                    Produce.objects.filter(
                        crates__cooling_unit=OuterRef("id"),
                        crates__in=Crate.generate_checkedin_crates_subquery(),
                    )
                ),
            )
        ), many=True)

    def create(self, validated_data):

        location = validated_data.pop("location")
        power_options = self.context["request"].data["power_options"]
        location_instance = Location.objects.get(id=location.id)
        operators = validated_data.pop("operators")

        cooling_unit_instance = CoolingUnit.objects.create(
            **validated_data,
            location=location_instance,
            date_creation=datetime.now(),
            date_last_modified=datetime.now()
        )
        power_options["cooling_unit"] = cooling_unit_instance.id
        power_options = add_power_default_values(power_options)
        power_serializer = CoolingUnitPowerSerializer(
            data=power_options,
        )

        if power_serializer.is_valid():
            power_serializer.save()
        else:
            print(
                "Serializer is not valid. Errors:",
                power_serializer.errors,
                power_options,
                validated_data,
            )

        for o in operators:
            operator = Operator.objects.get(user_id=o.id)
            cooling_unit_instance.operators.add(operator.user.id)
            operator_assigned = OperatorAssignedCoolingUnit.objects.create(
                operator=operator.user, date=datetime.now()
            )
            cooling_unit_instance.date_operator_assigned.add(operator_assigned.id)

        request_data = self.context["request"].data

        # json.loads convert all to string but does not revert them to initial type

        crops = [int(value) for value in request_data["crops"]]

        # Get all crops available in the cooling unit country
        country_name = location_instance.company.country.name
        filter_country = False
        for c in Country.objects.all():
            if c.country.name == country_name:
                filter_country = True
                break

        all_crops = []
        if filter_country:
            all_crops = Crop.objects.filter(
                countryRelated__country__name=country_name
            ).order_by("name")
        else:
            all_crops = Crop.objects.all().order_by("name")

        pricing_type = "FIXED" if request_data["fixed_price"] else "PERIODICITY"
        fixed_rate = request_data["price"] if request_data["fixed_price"] else 0
        daily_rate = request_data["price"] if not request_data["fixed_price"] else 0

        if request_data["sensor"]:
            sensor = request_data["sensor_data"]

            if sensor["type"] in ["ecozen", "figorr", "ubibot", "victron"]:
                SensorIntegration.objects.create(
                    type=sensor["type"],
                    source_id=sensor["source_id"],
                    username=sensor.get("username", ""),
                    password=sensor.get("password", ""),
                    cooling_unit_id=cooling_unit_instance.id,
                    date_sensor_first_linked=datetime.now(),
                    date_sensor_modified=datetime.now(),
                )
            else:
                print("Sensor type not found", sensor["type"], cooling_unit_instance.id, datetime.now())
            load_temperature(cooling_unit_instance)
        # When creating a new cooling unit, assign all the crops in the country to it
        # The available crops for the cooling unit have active=True
        for crop in all_crops:
            pricing_instance = Pricing.objects.create(
                pricing_type=pricing_type, fixed_rate=fixed_rate, daily_rate=daily_rate
            )
            available_crop = (
                True
                if crop.id in crops
                else (True if crop.name in ["Other", "Others"] else False)
            )
            CoolingUnitCrop.objects.create(
                crop_id=crop.id,
                cooling_unit=cooling_unit_instance,
                pricing=pricing_instance,
                active=available_crop,
            )
        return cooling_unit_instance

    def update(self, instance, validated_data):
        operators = validated_data.pop("operators")
        for operator in instance.operators.all():
            if operator in operators:
                continue
            else:
                instance.operators.remove(operator)
                operator_assigned = OperatorAssignedCoolingUnit.objects.filter(
                    operator=operator, assigned_cooling_unit_operators=instance
                ).delete()
        for o in operators:
            if o in instance.operators.all():
                continue
            else:
                operator = Operator.objects.get(user_id=o.id)
                instance.operators.add(operator.user.id)
                operator_assigned = OperatorAssignedCoolingUnit.objects.create(
                    operator=operator.user, date=datetime.now()
                )
                instance.date_operator_assigned.add(operator_assigned.id)

        instance.date_last_modified = datetime.now().astimezone()
        instance.save()

        request_data = self.context["request"].data

        # print("power_options", request_data['power_options'])
        if request_data["power_options"] and request_data["power_options"] != {}:

            power_options_update = add_power_default_values(
                request_data["power_options"]
            )
            # print("power_options_update", power_options_update)
            power_options_instance = CoolingUnitPower.objects.filter(
                cooling_unit=instance
            ).update(**power_options_update)

            # print("power_options_instance", power_options_instance, power_options_instance==0)
            # create a new entry if no existing entry was updated
            if power_options_instance == 0:
                CoolingUnitPower.objects.create(
                    **power_options_update, cooling_unit=instance
                )

        if request_data.get("sensor") and request_data.get("sensor_data"):
            sensor_data = request_data["sensor_data"]

            sensor_instance, created = SensorIntegration.objects.get_or_create(
                cooling_unit=instance
            )

            new_source_id = sensor_data.get("source_id", sensor_instance.source_id)

            if created:
                sensor_instance.date_sensor_first_linked = datetime.now()
            else:
                if not sensor_instance.date_sensor_first_linked and sensor_instance.source_id == new_source_id:
                    sensor_instance.date_sensor_first_linked = sensor_instance.date_sensor_modified or datetime.now()
                elif sensor_instance.source_id != new_source_id:
                    sensor_instance.date_sensor_first_linked = datetime.now()

            sensor_instance.type = sensor_data["type"]
            sensor_instance.username = sensor_data["username"]
            sensor_instance.password = sensor_data["password"]
            sensor_instance.source_id = new_source_id
            sensor_instance.date_sensor_modified = datetime.now()
            
            sensor_instance.save()

            load_temperature(instance)

        crop_updates = request_data["crop_updates"]
        current_crops = CoolingUnitCrop.objects.filter(cooling_unit=instance).values(
            "crop_id"
        )

        for crop in current_crops:
            CoolingUnitCrop.objects.filter(
                cooling_unit=instance, crop_id=crop["crop_id"]
            ).exclude(Q(crop__name="Other") | Q(crop__name="Others")).update(
                active=False
            )

        # If a crop in the request is not already attached to this cooling unit, add it with
        # the default price of the other crops

        for cropUpdate in crop_updates:
            # if crop doesn't exist yet, create it with default pricing in current cooling unit and set to active
            if {"crop_id": cropUpdate["id"]} not in current_crops:
                new_pricing_instance = Pricing.objects.create(
                    pricing_type=cropUpdate["pricing_type"],
                    fixed_rate=cropUpdate["fixed_rate"],
                    daily_rate=cropUpdate["daily_rate"],
                )
                cu_crop = CoolingUnitCrop.objects.create(
                    crop_id=cropUpdate["id"],
                    cooling_unit=instance,
                    pricing=new_pricing_instance,
                    active=True,
                )
            else:
                cu_crop = CoolingUnitCrop.objects.filter(
                    cooling_unit=instance, crop_id=cropUpdate["id"]
                ).first()
                CoolingUnitCrop.objects.filter(
                    cooling_unit=instance, crop_id=cropUpdate["id"]
                ).update(active=True)
                # print("updated cu_crop: ", cu_crop.pricing.id, cu_crop.id)

            # Update the pricing of that crop based on the latest value passed
            Pricing.objects.filter(id=cu_crop.pricing.id).update(
                pricing_type=cropUpdate["pricing_type"],
                fixed_rate=cropUpdate["fixed_rate"],
                daily_rate=cropUpdate["daily_rate"],
            )

        # Make sure that cooling unit has commodity 'Other' active for each category
        other_crops = Crop.objects.filter(name__in=["Other", "Others"])
        pricing_instance = Pricing.objects.get(id=request_data["pricing_id"])

        # update default pricing + pricing for others based on the default
        pricing_instance.pricing_type = (
            "FIXED" if request_data["fixed_price"] else "PERIODICITY"
        )
        pricing_instance.fixed_rate = (
            request_data["price"] if request_data["fixed_price"] else 0
        )
        pricing_instance.daily_rate = (
            request_data["price"] if not request_data["fixed_price"] else 0
        )
        pricing_instance.save()

        for other_type in other_crops:
            has_other = CoolingUnitCrop.objects.filter(
                cooling_unit=instance, crop_id=other_type.id
            ).exists()
            if not has_other:
                new_pricing_instance = Pricing.objects.create(
                    pricing_type=cropUpdate["pricing_type"],
                    fixed_rate=cropUpdate["fixed_rate"],
                    daily_rate=cropUpdate["daily_rate"],
                )
                CoolingUnitCrop.objects.create(
                    crop_id=other_type.id,
                    cooling_unit=instance,
                    pricing=new_pricing_instance,
                    active=True,
                )
            else:
                CoolingUnitCrop.objects.filter(
                    cooling_unit=instance, crop_id=other_type.id
                ).update(active=True)

        return super().update(instance, validated_data)

    def get_date_operator_assigned(self, instance):
        operators_assigned = instance.date_operator_assigned.all()
        return OperatorAssignedCoolingUnitSerializer(
            operators_assigned, many=True
        ).data

    def get_crops(self, instance):
        cu_crops = instance.crop_cooling_unit.all()

        return [
            {
                "id": crop.id,
                "crop_id": crop.crop.id,
                "active": crop.active,
                "pricing": {
                    "id": crop.pricing.id,
                    "pricing_type": crop.pricing.pricing_type,
                    "fixed_rate": crop.pricing.fixed_rate,
                    "daily_rate": crop.pricing.daily_rate,
                } if crop.pricing else None,
            } for crop in cu_crops
        ]

    def _get_latest_spec_temperature(self, instance):
        latest_spec_temperature_value = getattr(instance, "latest_spec_temperature_value", False)
        latest_spec_temperature_datetime_stamp = getattr(instance, "latest_spec_temperature_datetime_stamp", False)

        if latest_spec_temperature_value is not False and latest_spec_temperature_datetime_stamp is not False:
            return latest_spec_temperature_value, latest_spec_temperature_datetime_stamp

        try:
            latest_spec_temperature = instance.specification_cooling_unit.filter(specification_type="TEMPERATURE").latest("datetime_stamp")

            if latest_spec_temperature:
                return latest_spec_temperature.value, latest_spec_temperature.datetime_stamp
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
        total_weight = instance.crate_cooling_unit.aggregate(
            total=Sum("weight")
        )["total"] or 0

        if total_weight == 0:
            return []

        commodity_infos = (
            instance.crate_cooling_unit
            .filter(weight__gt=0)
            .values(
                crop_name=F("produce__crop__name"),
                optimal_storage_temperature=F("produce__crop__optimal_storage_temperature"),
            )
            .annotate(
                combined_weight=Sum("weight"),
                crates_number=Count("id"),
            )
        )

        return [
            {
                "commodity": info["crop_name"],
                "percentage": math.ceil((info["combined_weight"] / total_weight) * 100) if total_weight else 0,
                "combined_weight": float(info["combined_weight"]),
                "crates_number": info["crates_number"],
                "optimal_storage_temperature": info["optimal_storage_temperature"],
            }
            for info in commodity_infos
        ]

    def get_commodity_total(self, instance):
        # Group crates by crop and calculate total weight for each group
        grouped_weights = (
            instance.crate_cooling_unit
            .values("produce__crop")  # Group by crop
            .annotate(total_weight=Sum("weight"))  # Calculate weight for each crop group
        )

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
        filtered_crop = instance.crop_cooling_unit.filter(crop_id__in=[77, 1]).order_by("-crop_id").first()

        if not filtered_crop or not filtered_crop.pricing:
            return None

        pricing = filtered_crop.pricing
        pricing_value = pricing.daily_rate if pricing.pricing_type == "PERIODICITY" else pricing.fixed_rate

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
                default=None
            )

        # No movements prefetched
        try:
            latest_movement = Movement.objects.filter(checkins__produces__crates__cooling_unit=instance.id).distinct().order_by("-date").latest("date")
            return latest_movement.date if latest_movement else None
        except:
            return None


    # Cooling unit can only be deleted if all produces have the status of checkout complete as true
    def get_can_delete(self, instance):
        has_checked_in_produce_annotated = getattr(instance, "has_checked_in_produce", None)

        if has_checked_in_produce_annotated is not None:
            return not has_checked_in_produce_annotated

        return not Produce.objects.filter(
            Q(crates__cooling_unit=instance) & Exists(Crate.generate_checkedin_crates_subquery())
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
