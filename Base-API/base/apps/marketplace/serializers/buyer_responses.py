from rest_framework import serializers

from base.apps.marketplace.models import Order, OrderCrateItem

from .common import OrderPickupDetailSerializer


class BuyerOrderCrateItemSerializer(serializers.ModelSerializer):
    market_listed_crate_id = serializers.PrimaryKeyRelatedField(read_only=True)
    coupon_id = serializers.PrimaryKeyRelatedField(read_only=True)

    ordered_entire_crate = serializers.BooleanField()
    ordered_produce_weight = serializers.FloatField()

    crate_available_weight = serializers.FloatField(source="frozen_crate_available_weight")
    produce_price_per_kg = serializers.FloatField(source="frozen_produce_price_per_kg")

    produce_amount = serializers.FloatField(source="cmp_produce_amount", read_only=True)
    cooling_fees_amount = serializers.FloatField(source="cmp_cooling_fees_amount", read_only=True)
    discount_amount = serializers.FloatField(source="cmp_discount_amount", read_only=True)
    total_amount = serializers.FloatField(source="cmp_total_amount", read_only=True)

    # Getters
    rel_coupon_code = serializers.CharField(source='coupon.code', read_only=True)
    rel_crate_id = serializers.PrimaryKeyRelatedField(source='market_listed_crate.crate.id', read_only=True)
    rel_crop_id = serializers.PrimaryKeyRelatedField(source='market_listed_crate.crate.produce.crop', read_only=True)
    rel_cooling_unit_id = serializers.PrimaryKeyRelatedField(source='market_listed_crate.crate.cooling_unit', read_only=True)
    rel_company_id = serializers.PrimaryKeyRelatedField(source='market_listed_crate.crate.cooling_unit.location.company', read_only=True)
    rel_crate_remaining_shelf_life = serializers.PrimaryKeyRelatedField(source='market_listed_crate.crate.remaining_shelf_life', read_only=True)
    rel_checkin_movement_code = serializers.PrimaryKeyRelatedField(source='market_listed_crate.crate.produce.checkin.movement.code', read_only=True)

    owned_by_user_id = serializers.PrimaryKeyRelatedField(source='market_listed_crate.crate.produce.checkin.owned_by_user', read_only=True)
    owned_on_behalf_of_company_id = serializers.PrimaryKeyRelatedField(source='market_listed_crate.crate.produce.checkin.owned_on_behalf_of_company', read_only=True)

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

            # Ownership
            'owned_by_user_id',
            'owned_on_behalf_of_company_id',

            # Frozen
            'crate_available_weight',
            'produce_price_per_kg',

            # Computed
            'produce_amount',
            'cooling_fees_amount',
            'discount_amount',
            'total_amount',
        ]


class BuyerCartSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    items = BuyerOrderCrateItemSerializer(many=True)  # Use the related name
    pickup_details = OrderPickupDetailSerializer(many=True)
    currency = serializers.CharField()

    # Computed
    total_produce_amount = serializers.FloatField(source="cmp_total_produce_amount",read_only=True)
    total_cooling_fees_amount = serializers.FloatField(source="cmp_total_cooling_fees_amount",read_only=True)
    total_coldtivate_amount = serializers.FloatField(source="cmp_total_coldtivate_amount",read_only=True)
    total_discount_amount = serializers.FloatField(source="cmp_total_discount_amount",read_only=True)
    total_payment_fees_amount = serializers.FloatField(source="cmp_total_payment_fees_amount",read_only=True)
    total_amount = serializers.FloatField(source="cmp_total_amount",read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'created_at',
            'items',
            'pickup_details',
            'owned_on_behalf_of_company_id',
            'currency',

            # Computed
            'total_produce_amount',
            'total_cooling_fees_amount',
            'total_coldtivate_amount',
            'total_discount_amount',
            'total_payment_fees_amount',
            'total_amount',
        ]



class BuyerOrderSerializer(serializers.ModelSerializer):
    items = BuyerOrderCrateItemSerializer(many=True)  # Use the related name
    pickup_details = OrderPickupDetailSerializer(many=True)

    status = serializers.ChoiceField(choices=Order.Status.choices)  # Assuming Order has a Status enum or choices
    currency = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)
    created_by_user = serializers.PrimaryKeyRelatedField(read_only=True)  # Assuming it's a ForeignKey to User

    payment_paid_at = serializers.DateTimeField(source="paid_at", allow_null=True, required=False)  # Optional field
    payment_amount_paid = serializers.FloatField(source="amount_paid",allow_null=True, required=False)  # Optional field

    # Computed
    total_produce_amount = serializers.FloatField(source="cmp_total_produce_amount",read_only=True)
    total_cooling_fees_amount = serializers.FloatField(source="cmp_total_cooling_fees_amount",read_only=True)
    total_coldtivate_amount = serializers.FloatField(source="cmp_total_coldtivate_amount",read_only=True)
    total_discount_amount = serializers.FloatField(source="cmp_total_discount_amount",read_only=True)
    total_payment_fees_amount = serializers.FloatField(source="cmp_total_payment_fees_amount",read_only=True)
    total_amount = serializers.FloatField(source="cmp_total_amount",read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'pickup_details',

            'status',
            'currency',
            'created_at',
            'created_by_user',
            'items',
            'owned_on_behalf_of_company_id',

            # Payment
            'payment_paid_at',
            'payment_amount_paid',

            # Computed
            'total_produce_amount',
            'total_cooling_fees_amount',
            'total_coldtivate_amount',
            'total_discount_amount',
            'total_payment_fees_amount',
            'total_amount',
        ]
