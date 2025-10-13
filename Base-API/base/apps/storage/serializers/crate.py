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
    
    # Calculated pricing fields
    calculated_total_price = serializers.SerializerMethodField()
    calculated_daily_rate = serializers.SerializerMethodField()
    calculated_fixed_rate = serializers.SerializerMethodField()
    effective_pricing_type = serializers.SerializerMethodField()

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
            
            # Calculated pricing fields
            "calculated_total_price",
            "calculated_daily_rate", 
            "calculated_fixed_rate",
            "effective_pricing_type",
        )

    def get_cooling_unit_metric(self, instance):
        return instance.cooling_unit.metric

    def get_name(self, instance):
        return instance.produce.crop.name

    def get_crop_image(self, instance):
        return instance.produce.crop.image.name

    def get_pricing(self, instance):
        cu = instance.cooling_unit

        # Try to get the pre-fetched 'all_crop_cooling_units' attribute first
        if hasattr(cu, "all_crop_cooling_units"):
            # `all_crop_cooling_units` is a list (from Prefetch with to_attr)
            # Find the first item with a matching crop
            cu_crop = next((c for c in getattr(cu, "all_crop_cooling_units", []) if c.crop_id == instance.produce.crop_id), None)
        else:
            # Fallback: query directly from DB (slower)
            cu_crop = cu.crop_cooling_unit.filter(crop=instance.produce.crop).first()

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
        run_dt = instance.run_dt
        return (identifier and company) and (run_dt or instance.modified_dt != None)

    def get_remaining_shelf_life(self, instance):
        if instance.run_dt:
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
        is_listed_in_the_marketplace = getattr(instance, "is_listed_in_the_marketplace", None)
        if is_listed_in_the_marketplace is not None:
            return is_listed_in_the_marketplace

        # Check if the crate is listed in the marketplace
        return instance.market_listed_crates.filter(delisted_at__isnull=True).exists()

    def get_locked_within_pending_orders(self, instance):
        is_locked_within_pending_orders = getattr(instance, "is_locked_within_pending_orders", None)
        if is_locked_within_pending_orders is not None:
            return is_locked_within_pending_orders

        return (
            instance.market_listed_crates
            .filter(
                delisted_at__isnull=True,
                cmp_weight_locked_in_payment_pending_orders_in_kg__gt=0,
            )
            .exists()
        )
    
    def get_calculated_total_price(self, instance):
        """Return the backend-calculated total price for this crate"""
        return instance.price_per_crate_per_pricing_type
    
    def get_calculated_daily_rate(self, instance):
        """Return the daily rate from the pricing configuration"""
        pricing = self.get_pricing(instance)
        if pricing and len(pricing) > 0:
            return pricing[0].get('daily_rate', 0)
        return 0
        
    def get_calculated_fixed_rate(self, instance):
        """Return the fixed rate from the pricing configuration"""  
        pricing = self.get_pricing(instance)
        if pricing and len(pricing) > 0:
            return pricing[0].get('fixed_rate', 0)
        return 0
        
    def get_effective_pricing_type(self, instance):
        """Return the pricing type (FIXED or PERIODICITY) for this crate"""
        pricing = self.get_pricing(instance)
        if pricing and len(pricing) > 0:
            return pricing[0].get('pricing_type')
        return None
