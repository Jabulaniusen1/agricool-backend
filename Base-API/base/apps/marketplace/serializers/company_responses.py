from rest_framework import serializers

from base.apps.marketplace.models import Order, OrderCrateItem


class CompanyOrderCrateItemSerializer(serializers.ModelSerializer):
    """
    Serializer for OrderCrateItem objects used in the company order overview.
    This serializer includes key details about the order item, such as the
    associated market listed crate, coupon information, ordered quantities, as
    well as frozen and computed pricing values.
    """
    # Basic fields with read-only relationships
    market_listed_crate_id = serializers.PrimaryKeyRelatedField(read_only=True)
    coupon_id = serializers.PrimaryKeyRelatedField(read_only=True)

    # Fields for the user's order choices
    ordered_entire_crate = serializers.BooleanField()
    ordered_produce_weight = serializers.FloatField()

    # Frozen values (captured at the time of ordering)
    crate_available_weight = serializers.FloatField(source="frozen_crate_available_weight")
    produce_price_per_kg = serializers.FloatField(source="frozen_produce_price_per_kg")

    # Computed pricing values (read-only)
    produce_amount = serializers.FloatField(source="cmp_produce_amount", read_only=True)
    cooling_fees_amount = serializers.FloatField(source="cmp_cooling_fees_amount", read_only=True)
    discount_amount = serializers.FloatField(source="cmp_discount_amount", read_only=True)
    total_amount = serializers.FloatField(source="cmp_total_amount", read_only=True)

    # Additional related fields (getters)
    rel_coupon_code = serializers.CharField(source='coupon.code', read_only=True)
    rel_crate_id = serializers.PrimaryKeyRelatedField(source='market_listed_crate.crate.id', read_only=True)
    rel_crop_id = serializers.PrimaryKeyRelatedField(source='market_listed_crate.crate.produce.crop', read_only=True)
    rel_cooling_unit_id = serializers.PrimaryKeyRelatedField(source='market_listed_crate.crate.cooling_unit', read_only=True)
    rel_company_id = serializers.PrimaryKeyRelatedField(source='market_listed_crate.crate.cooling_unit.location.company', read_only=True)
    rel_crate_remaining_shelf_life = serializers.PrimaryKeyRelatedField(source='market_listed_crate.crate.remaining_shelf_life', read_only=True)
    rel_checkin_movement_code = serializers.PrimaryKeyRelatedField(
        source='market_listed_crate.crate.produce.checkin.movement.code', read_only=True
    )

    class Meta:
        model = OrderCrateItem
        fields = [
            'market_listed_crate_id',
            'ordered_entire_crate',
            'ordered_produce_weight',
            'coupon_id',

            # Related FKs
            'rel_coupon_code',
            'rel_crate_id',
            'rel_crop_id',
            'rel_cooling_unit_id',
            'rel_company_id',
            'rel_crate_remaining_shelf_life',
            'rel_checkin_movement_code',

            # Frozen values
            'crate_available_weight',
            'produce_price_per_kg',

            # Computed values
            'produce_amount',
            'cooling_fees_amount',
            'discount_amount',
            'total_amount',
        ]


class CompanyOrderSerializer(serializers.ModelSerializer):
    """
    Serializer for Order objects in a company context.
    This serializer nests OrderCrateItemSerializer to include detailed information
    on each item in the order.
    """
    items = CompanyOrderCrateItemSerializer(many=True)  # Use the related name
    created_at = serializers.DateTimeField(read_only=True)
    payment_paid_at = serializers.DateTimeField(
        source="paid_at", allow_null=True, required=False, help_text="Timestamp when payment was made"
    )
    created_by_user = serializers.PrimaryKeyRelatedField(
        read_only=True, help_text="ID of the user who created the order"
    )
    currency = serializers.CharField(help_text="Currency of the order")

    class Meta:
        model = Order
        fields = [
            'id',
            'currency',
            'created_at',
            'items',
            'payment_paid_at',
            'created_by_user',
        ]
