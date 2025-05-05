from rest_framework import serializers

from base.apps.marketplace.models import Order, OrderCrateItem


class SellerOrderCrateItemSerializer(serializers.ModelSerializer):
    """
    Serializer for a seller's order crate items.
    
    This serializer includes details about the order item—such as which
    market-listed crate is involved, user inputs, frozen values at the time
    of ordering, and computed pricing values. It also provides related
    information via getter fields.
    """
    # Basic fields (read-only relationships)
    market_listed_crate_id = serializers.PrimaryKeyRelatedField(read_only=True)
    coupon_id = serializers.PrimaryKeyRelatedField(read_only=True)

    # Seller-provided fields
    ordered_entire_crate = serializers.BooleanField()
    ordered_produce_weight = serializers.FloatField()

    # Frozen values captured when the order was placed
    crate_available_weight = serializers.FloatField(source="frozen_crate_available_weight")
    produce_price_per_kg = serializers.FloatField(source="frozen_produce_price_per_kg")

    # Computed pricing values (read-only)
    produce_amount = serializers.FloatField(source="cmp_produce_amount", read_only=True)
    cooling_fees_amount = serializers.FloatField(source="cmp_cooling_fees_amount", read_only=True)
    discount_amount = serializers.FloatField(source="cmp_discount_amount", read_only=True)
    total_amount = serializers.FloatField(source="cmp_total_amount", read_only=True)

    # Getters for related data
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


class SellerOrderSerializer(serializers.ModelSerializer):
    """
    Serializer for seller orders.
    
    This serializer provides an overview of an order, including key order
    details and the list of nested order items.
    """
    items = SellerOrderCrateItemSerializer(many=True)
    created_at = serializers.DateTimeField(read_only=True)
    payment_paid_at = serializers.DateTimeField(
        source="paid_at", 
        allow_null=True, 
        required=False,
        help_text="Time when the payment was completed"
    )
    currency = serializers.CharField()

    class Meta:
        model = Order
        fields = [
            'id',
            'created_at',
            'currency',
            'items',
            'payment_paid_at',
        ]
