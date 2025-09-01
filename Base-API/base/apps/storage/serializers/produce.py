from datetime import datetime

from rest_framework import serializers

from ..models import Crate, Produce
from .crate import CrateSerializer


class ProduceSerializer(serializers.ModelSerializer):
    crop_id = serializers.SerializerMethodField()
    crop_name = serializers.SerializerMethodField()
    crop_image = serializers.SerializerMethodField()
    farmer_id = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    owner_contact = serializers.SerializerMethodField()
    minimum_remaining_shelf_life = serializers.SerializerMethodField()
    planned_days = serializers.SerializerMethodField()
    crates_amount = serializers.SerializerMethodField()
    movement_code = serializers.SerializerMethodField()
    crates_combined_weight = serializers.SerializerMethodField()
    crates_combined_cost = serializers.SerializerMethodField()
    current_storage_days = serializers.SerializerMethodField()
    has_digital_twin = serializers.SerializerMethodField()
    quality_dt = serializers.SerializerMethodField()
    run_dt = serializers.SerializerMethodField()
    additional_info = serializers.CharField(max_length=255)
    checked_in_crates = serializers.SerializerMethodField()

    owned_by_user_id = serializers.PrimaryKeyRelatedField(source='checkin.owned_by_user', read_only=True)
    owned_on_behalf_of_company_id = serializers.PrimaryKeyRelatedField(source='checkin.owned_on_behalf_of_company', read_only=True)

    operator_name = serializers.SerializerMethodField()
    operator_contact = serializers.SerializerMethodField()

    class Meta:
        model = Produce
        fields = (
            "id",
            "crop_id",
            "crop_name",
            "crop_image",
            "farmer_id",
            "minimum_remaining_shelf_life",
            "planned_days",
            "crates_amount",
            "movement_code",
            "cmp_checkout_completed",
            "crates_combined_weight",
            "crates_combined_cost",
            "current_storage_days",
            "has_digital_twin",
            "quality_dt",
            "run_dt",
            "additional_info",
            "checked_in_crates",

            "owner",
            "owner_contact",
            "owned_by_user_id",
            "owned_on_behalf_of_company_id",

            "operator_name",
            "operator_contact"
        )

    def get_crop_id(self, instance):
        return instance.crop.id

    def get_crop_name(self, instance):
        return instance.crop.name

    def get_crop_image(self, instance):
        if instance.picture:
            return str(instance.picture)
        return instance.crop.image.name

    def get_owner(self, instance):
        owned_on_behalf_of_company = instance.checkin.owned_on_behalf_of_company
        if owned_on_behalf_of_company:
            return f"{owned_on_behalf_of_company.name}"

        owned_by_user = instance.checkin.owned_by_user
        return f"{owned_by_user.first_name} {owned_by_user.last_name}"

    def get_operator_name(self, instance):
        movement = getattr(instance.checkin, 'movement', None)
        if movement and movement.operator and movement.operator.user:
          operator_user = movement.operator.user
          return f"{operator_user.first_name} {operator_user.last_name}"
        return None

    def get_farmer_id(self, instance):
        farmer = getattr(instance.checkin.owned_by_user, 'farmer', None)
        return farmer.id if farmer else None

    def get_owner_contact(self, instance):
        return str(instance.checkin.owned_by_user.phone)

    def get_operator_contact(self, instance):
        movement = getattr(instance.checkin, 'movement', None)
        if movement and movement.operator and movement.operator.user:
          operator_user = movement.operator.user
          return str(operator_user.phone)
        return None

    def get_minimum_remaining_shelf_life(self, instance):
        crates = instance.crates.filter(weight__gt=0)
        remaining_shelf_life_values = crates.values_list('remaining_shelf_life', flat=True)
        return min([life for life in remaining_shelf_life_values if life is not None], default=None)


    def get_run_dt(self, instance):
        identifier = bool(instance.crop.digital_twin_identifier)
        first_crate = instance.crates.filter(weight__gt=0).first()
        if first_crate:
            company = first_crate.cooling_unit.location.company.digital_twin
            return identifier and company and (first_crate.runDT or first_crate.modified_dt)
        return None

    def get_planned_days(self, instance):
        if Crate.objects.filter(produce=instance.id, weight__gt=0):
            return Crate.objects.filter(produce=instance.id, weight__gt=0)[
                0
            ].planned_days
        else:
            return None

    def get_crates_amount(self, instance):
        return instance.crates.filter(weight__gt=0).count()

    def get_movement_code(self, instance):
        return instance.checkin.movement.code

    def get_crates_combined_weight(self, instance):
        return sum(crate.weight for crate in instance.crates.filter(weight__gt=0))

    def get_crates_combined_cost(self, instance):
        return sum(crate.price_per_crate_per_pricing_type for crate in instance.crates.filter(weight__gt=0))

    def get_current_storage_days(self, instance):
        checkin_date = instance.checkin.movement.date.replace(tzinfo=None).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        duration = (midnight - checkin_date).days
        return 1 if duration == 0 else duration

    def get_has_digital_twin(self, instance):
        identifier = True if instance.crop.digital_twin_identifier else False
        crate = Crate.objects.filter(produce=instance, weight__gt=0).first()
        if crate:
            company = crate.cooling_unit.location.company.digital_twin
            return identifier and company
        else:
            return None

    def get_quality_dt(self, instance):
        crates = instance.crates.filter(weight__gt=0)
        quality = None

        for crate in crates:
            if crate.quality_dt and crate.quality_dt != -1:
                quality = crate.quality_dt
            else:
                quality = None

        return quality

    def get_checked_in_crates(self, instance):
        query_set = instance.crates.filter(weight__gt=0)
        return CrateSerializer(query_set, many=True).data
