from datetime import datetime

from django.utils import timezone
from rest_framework import serializers

from ..models import Crate
from .pricing import PricingSerializer


class CrateSerializer(serializers.ModelSerializer):
    pricing = serializers.SerializerMethodField()
    cooling_unit_metric = serializers.SerializerMethodField()
    checkin_date = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    crop_image = serializers.SerializerMethodField()
    movement_code = serializers.SerializerMethodField()
    current_storage_days = serializers.SerializerMethodField()
    run_dt = serializers.SerializerMethodField()
    remaining_shelf_life = serializers.SerializerMethodField()
    tag = serializers.CharField(max_length=255)
    listed_in_the_marketplace = serializers.SerializerMethodField()
    locked_within_pending_orders = serializers.SerializerMethodField()

    class Meta:
        model = Crate
        fields = (
            "id",
            "produce",
            "cooling_unit",
            "weight",
            "initial_weight",
            "remaining_shelf_life",
            "planned_days",
            "pricing",
            "cooling_unit_metric",
            "checkin_date",
            "name",
            "crop_image",
            "movement_code",
            "current_storage_days",
            "run_dt",
            "quality_dt",
            "tag",
            "listed_in_the_marketplace",
            "locked_within_pending_orders",
            "cmp_fully_checked_out",
        )

    def get_cooling_unit_metric(self, instance):
        return instance.cooling_unit.metric

    def get_name(self, instance):
        return instance.produce.crop.name

    def get_crop_image(self, instance):
        return instance.produce.crop.image.name

    # I don't agree with the returned type of this attribute (array with single object), but
    # I'm trying not to break the frontend implementation during this optimization effort
    def get_pricing(self, instance):
        # Fetch the pricing using pre-fetched data (avoiding filter queries)
        cu_crop = instance.cooling_unit.crop_cooling_unit.filter(crop=instance.produce.crop).first()

        if cu_crop and cu_crop.pricing:
            return [PricingSerializer(cu_crop.pricing).data]

        return []

    def get_checkin_date(self, instance):
        return instance.produce.checkin.movement.date

    def get_quality_dt(self, instance):
        return instance.produce.quality_dt

    def get_movement_code(self, instance):
        return instance.produce.checkin.movement.code

    def get_current_storage_days(self, instance):
        checkin_date = instance.produce.checkin.movement.date.replace(
            tzinfo=None
        ).replace(hour=0, minute=0, second=0, microsecond=0)
        midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        duration = (midnight - checkin_date).days
        return 1 if duration == 0 else duration

    def get_run_dt(self, instance):
        identifier = True if instance.produce.crop.digital_twin_identifier else False
        company = instance.cooling_unit.location.company.digital_twin
        runDT = instance.runDT
        return (identifier and company) and (runDT or instance.modified_dt != None)

    def get_remaining_shelf_life(self, instance):
        if instance.runDT:
            if instance.remaining_shelf_life:
                return instance.remaining_shelf_life
            crate_with_data = instance.produce.crates.filter(
                remaining_shelf_life__isnull=False
            ).first()
            if crate_with_data:
                # Update remaining crates' shelf life
                instance.produce.crates.filter(
                    remaining_shelf_life__isnull=True
                ).update(
                    remaining_shelf_life=crate_with_data.remaining_shelf_life,
                    modified_dt=timezone.now(),
                    quality_dt=crate_with_data.quality_dt,
                )
                return crate_with_data.remaining_shelf_life
        return None

    def get_listed_in_the_marketplace(self, instance):
        # Check if the crate is listed in the marketplace
        return instance.market_listed_crates.filter(delisted_at__isnull=True).exists()

    def get_locked_within_pending_orders(self, instance):
        return (
            instance.market_listed_crates
            .filter(
                delisted_at__isnull=True,
                cmp_weight_locked_in_payment_pending_orders_in_kg__gt=0,
            )
            .exists()
        )
