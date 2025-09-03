from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from base.apps.storage.models import (
    CoolingUnit,
    CoolingUnitCrop,
    CoolingUnitPower,
    Crop,
    Pricing,
    SensorIntegration,
)
from base.apps.storage.serializers.operator_assigned_cooling_unit import (
    OperatorAssignedCoolingUnit,
)
from base.apps.storage.services.sensory import load_temperature
from base.apps.user.models import Country, Operator

# Power options constants
DEFAULT_ELECTRICITY_STORAGE_SYSTEM = "none" 
DEFAULT_THERMAL_STORAGE_METHOD = "none"

# Default pricing rates
DEFAULT_RATE_VALUE = 0


def add_power_default_values(power_options):
    if not power_options.get("pv_panel_type"):
        power_options["pv_panel_type"] = None

    if not power_options.get("refrigerant_type"):
        power_options["refrigerant_type"] = CoolingUnitPower.RefrigerantType.OTHER
    if not power_options.get("power_source"):
        power_options["power_source"] = CoolingUnitPower.PowerSource.PV_PANELS
    if not power_options.get("electricity_storage_system"):
        power_options["electricity_storage_system"] = DEFAULT_ELECTRICITY_STORAGE_SYSTEM
    if not power_options.get("thermal_storage_method"):
        power_options["thermal_storage_method"] = DEFAULT_THERMAL_STORAGE_METHOD

    return power_options


def create_cooling_unit_from_payload(payload):
    """
    Creates a CoolingUnit and all related objects (power_settings, crops, sensor, etc.)
    based on the raw request payload.
    Accepts operators as a list of user IDs OR a list of {"id": <user_id>} dicts.
    """

    location_id = payload["location"]
    operators = payload.get("operators", []) or []
    power_options = payload.get("power_options", {}) or {}
    crops_ids = [int(value) for value in payload.get("crops", [])]
    fixed_price = payload.get("fixed_price")
    price_value = payload.get("price")

    # 1) Create CoolingUnit
    cooling_unit = CoolingUnit.objects.create(
        name=payload["name"],
        metric=payload["metric"],
        location_id=location_id,  # FK id
        date_creation=timezone.now(),
        date_last_modified=timezone.now(),
        cooling_unit_type=payload.get("cooling_unit_type"),
        public=payload.get("public", False),
        editable_checkins=payload.get("editable_checkins", False),
        # Add missing capacity fields
        capacity_in_metric_tons=payload.get("capacity_in_metric_tons"),
        capacity_in_number_crates=payload.get("capacity_in_number_crates"),
        # Add other physical dimension fields that might be missing
        room_height=payload.get("room_height"),
        room_length=payload.get("room_length"),
        room_width=payload.get("room_width"),
        room_weight=payload.get("room_weight"),
        crate_weight=payload.get("crate_weight"),
        crate_width=payload.get("crate_width"),
        crate_length=payload.get("crate_length"),
        crate_height=payload.get("crate_height"),
        food_capacity_in_metric_tons=payload.get("food_capacity_in_metric_tons"),
    )

    # 2) Add operators (support int or {"id": int})
    for o in operators:
        user_id = o.get("id") if isinstance(o, dict) else o
        try:
            operator = Operator.objects.get(user_id=int(user_id))
            cooling_unit.operators.add(operator.user.id)
        except (Operator.DoesNotExist, TypeError, ValueError):
            # skip unknown or malformed entries
            continue

    # 3) Power settings
    power_options["cooling_unit"] = cooling_unit
    power_options = add_power_default_values(power_options)
    CoolingUnitPower.objects.create(**power_options)

    # 4) Sensor (optional)
    if payload.get("sensor") and payload.get("sensor_data"):
        print("Creating sensor integration for cooling unit")
        sensor_data = payload["sensor_data"]
        SensorIntegration.objects.create(
            type=sensor_data["type"],
            source_id=sensor_data["source_id"],
            username=sensor_data.get("username", ""),
            password=sensor_data.get("password", ""),
            cooling_unit=cooling_unit,
            date_sensor_first_linked=timezone.now(),
            date_sensor_modified=timezone.now(),
        )
        # Set the cooling unit sensor flag to True
        cooling_unit.sensor = True
        cooling_unit.save()
        load_temperature(cooling_unit)

    # 5) Crop + pricing setup
    country_name = cooling_unit.location.company.country.name

    if Country.objects.filter(country__name=country_name).exists():
        available_crops = Crop.objects.filter(countryRelated__country__name=country_name)
    else:
        available_crops = Crop.objects.all()

    pricing_type = (
        Pricing.PricingType.FIXED
        if fixed_price
        else Pricing.PricingType.PERIODICITY
    )
    fixed_rate = price_value if fixed_price else DEFAULT_RATE_VALUE
    daily_rate = price_value if not fixed_price else DEFAULT_RATE_VALUE

    for crop in available_crops:
        pricing = Pricing.objects.create(
            pricing_type=pricing_type,
            fixed_rate=fixed_rate,
            daily_rate=daily_rate,
        )
        active = crop.id in crops_ids or crop.name in ["Other", "Others"]
        CoolingUnitCrop.objects.create(
            crop=crop,
            cooling_unit=cooling_unit,
            pricing=pricing,
            active=active,
        )

    return cooling_unit


def update_cooling_unit_from_payload(payload, cooling_unit_id):
    """
    Fully updates a CoolingUnit and its related objects (operators, power settings,
    sensor, crops/pricing, etc.) based on the raw request payload.
    """
    try:
        cu = CoolingUnit.objects.get(id=cooling_unit_id)
    except CoolingUnit.DoesNotExist:
        raise ValueError(f"CoolingUnit with id {cooling_unit_id} does not exist")

    # 1) Replace operators
    operator_ids = payload.get("operators", [])
    current_ids = list(cu.operators.values_list("id", flat=True))

    # remove old
    for old_id in current_ids:
        if old_id not in operator_ids:
            cu.operators.remove(old_id)
            OperatorAssignedCoolingUnit.objects.filter(
                operator_id=old_id, assigned_cooling_unit_operators=cu
            ).delete()

    # add new
    for new_id in operator_ids:
        if new_id not in current_ids:
            try:
                operator = Operator.objects.get(user_id=new_id)
                cu.operators.add(operator.user.id)
                op_assigned = OperatorAssignedCoolingUnit.objects.create(
                    operator=operator.user, date=datetime.now()
                )
                cu.date_operator_assigned.add(op_assigned.id)
            except Operator.DoesNotExist:
                continue

    # update "basic" fields
    cu.date_last_modified = datetime.now()
    cu.cooling_unit_type = payload.get("cooling_unit_type", cu.cooling_unit_type)
    cu.public = payload.get("public", cu.public)
    cu.editable_checkins = payload.get("editable_checkins", cu.editable_checkins)
    
    # Update capacity and dimension fields if provided
    if "capacity_in_metric_tons" in payload:
        cu.capacity_in_metric_tons = payload.get("capacity_in_metric_tons")
    if "capacity_in_number_crates" in payload:
        cu.capacity_in_number_crates = payload.get("capacity_in_number_crates")
    if "room_height" in payload:
        cu.room_height = payload.get("room_height")
    if "room_length" in payload:
        cu.room_length = payload.get("room_length")
    if "room_width" in payload:
        cu.room_width = payload.get("room_width")
    if "room_weight" in payload:
        cu.room_weight = payload.get("room_weight")
    if "crate_weight" in payload:
        cu.crate_weight = payload.get("crate_weight")
    if "crate_width" in payload:
        cu.crate_width = payload.get("crate_width")
    if "crate_length" in payload:
        cu.crate_length = payload.get("crate_length")
    if "crate_height" in payload:
        cu.crate_height = payload.get("crate_height")
    if "food_capacity_in_metric_tons" in payload:
        cu.food_capacity_in_metric_tons = payload.get("food_capacity_in_metric_tons")
    
    cu.save()

    # 2) Power settings
    power_opts = payload.get("power_options", {})
    if power_opts:
        power_opts = add_power_default_values(power_opts)
        updated_count = CoolingUnitPower.objects.filter(cooling_unit=cu).update(
            **power_opts
        )
        if updated_count == 0:
            CoolingUnitPower.objects.create(**power_opts, cooling_unit=cu)

    # 3) Sensor
    if payload.get("sensor") and payload.get("sensor_data"):
        sd = payload["sensor_data"]
        
        sensor, created = SensorIntegration.objects.get_or_create(
            cooling_unit=cu,
            defaults={
                'type': sd["type"],
                'source_id': sd["source_id"],
                'username': sd.get("username", ""),
                'password': sd.get("password", ""),
                'date_sensor_first_linked': datetime.now(),
                'date_sensor_modified': datetime.now(),
            }
        )
        
        if not created:
            # Update existing sensor
            new_source_id = sd.get("source_id", sensor.source_id)
            
            if (not sensor.date_sensor_first_linked and sensor.source_id == new_source_id):
                sensor.date_sensor_first_linked = sensor.date_sensor_modified or datetime.now()
            elif sensor.source_id != new_source_id:
                sensor.date_sensor_first_linked = datetime.now()

            sensor.type = sd["type"]
            sensor.username = sd["username"]
            sensor.password = sd["password"]
            sensor.source_id = new_source_id
            sensor.date_sensor_modified = datetime.now()
            sensor.save()
        
        # Set the cooling unit sensor flag to True
        cu.sensor = True
        cu.save()
        load_temperature(cu)

    # 4) Crops + pricing
    crop_updates = payload.get("crop_updates", [])
    current_crop_ids = list(
        CoolingUnitCrop.objects.filter(cooling_unit=cu).values_list(
            "crop_id", flat=True
        )
    )

    # deactivate all (except "Other")
    CoolingUnitCrop.objects.filter(cooling_unit=cu).exclude(
        Q(crop__name="Other") | Q(crop__name="Others")
    ).update(active=False)

    for cu_data in crop_updates:
        crop_id = cu_data["id"]
        if crop_id not in current_crop_ids:
            pricing = Pricing.objects.create(
                pricing_type=cu_data["pricing_type"],
                fixed_rate=cu_data["fixed_rate"],
                daily_rate=cu_data["daily_rate"],
            )
            CoolingUnitCrop.objects.create(
                crop_id=crop_id,
                cooling_unit=cu,
                pricing=pricing,
                active=True,
            )
        else:
            try:
                cuc = CoolingUnitCrop.objects.get(cooling_unit=cu, crop_id=crop_id)
                cuc.active = True
                cuc.save()
                Pricing.objects.filter(id=cuc.pricing.id).update(
                    pricing_type=cu_data["pricing_type"],
                    fixed_rate=cu_data["fixed_rate"],
                    daily_rate=cu_data["daily_rate"],
                )
            except CoolingUnitCrop.DoesNotExist:
                continue

    # default "other" crops must remain active
    other_crops = Crop.objects.filter(name__in=["Other", "Others"])
    default_price = payload["price"]
    default_is_fixed = payload["fixed_price"]

    for oc in other_crops:
        obj, created = CoolingUnitCrop.objects.get_or_create(cooling_unit=cu, crop=oc)
        obj.active = True
        obj.save()
        if created:
            # create default pricing
            Pricing.objects.create(
                pricing_type=Pricing.PricingType.FIXED if default_is_fixed else Pricing.PricingType.PERIODICITY,
                fixed_rate=default_price if default_is_fixed else DEFAULT_RATE_VALUE,
                daily_rate=default_price if not default_is_fixed else DEFAULT_RATE_VALUE,
                id=obj.pricing_id,
            )

    # update default pricing itself
    try:
        default_pricing = Pricing.objects.get(id=payload["pricing_id"])
        default_pricing.pricing_type = Pricing.PricingType.FIXED if default_is_fixed else Pricing.PricingType.PERIODICITY
        default_pricing.fixed_rate = default_price if default_is_fixed else DEFAULT_RATE_VALUE
        default_pricing.daily_rate = default_price if not default_is_fixed else DEFAULT_RATE_VALUE
        default_pricing.save()
    except Pricing.DoesNotExist:
        pass

    return cu
