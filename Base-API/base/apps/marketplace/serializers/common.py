import re

from rest_framework import serializers

from base.apps.marketplace.models import (CompanyDeliveryContact, Coupon,
                                          MarketListedCrate, OrderPickupDetails,
                                          PaystackAccount)
from base.utils.currencies import quantitize_float


class OrderPickupDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for order pickup details, retrieving the cooling unit ID and
    the pickup method.
    """
    cooling_unit_id = serializers.PrimaryKeyRelatedField(read_only=True)
    pickup_method = serializers.ChoiceField(
        choices=OrderPickupDetails.PickUpMethod.choices,
        read_only=True
    )


    class Meta:
        model = OrderPickupDetails
        fields = [
            'cooling_unit_id',
            'pickup_method',
        ]


class CompanyDeliveryContactSerializer(serializers.ModelSerializer):
    """
    Serializer for the company delivery contact details.
    """
    cooling_unit_id = serializers.SerializerMethodField()

    class Meta:
        model = CompanyDeliveryContact
        fields = [
            'id',
            'delivery_company_name',
            'contact_name',
            'phone',
            'company_id',
            'cooling_unit_id',
        ]

    def get_cooling_unit_id(self, obj):
        """
        Returns the cooling unit ID if available.
        """
        return getattr(obj, 'cooling_unit_id', None)


class CouponSerializer(serializers.ModelSerializer):
    """
    Serializer for Coupon objects.
    """
    created_at = serializers.DateTimeField()
    revoked_at = serializers.DateTimeField()
    code = serializers.CharField()
    discount_percentage = serializers.FloatField()

    class Meta:
        model = Coupon
        fields = [
            'id',
            'created_at',
            'revoked_at',
            'code',
            'discount_percentage',
        ]

    def validate_code(self, value):
        """
        Ensures that the coupon code is not empty and removes non-alphanumeric characters,
        converting it to uppercase.
        """
        if value.strip() == '':
            raise serializers.ValidationError("Coupon code cannot be empty.")
        return re.sub(r'[^A-Za-z0-9]', '', value.strip().upper())


class MarketListedCrateSerializer(serializers.ModelSerializer):
    """
    Serializer for MarketListedCrate objects.
    Exposes computed values and related foreign key information.
    """
    # Computed fields
    last_updated_at = serializers.DateTimeField(source='cmp_last_updated_at', read_only=True)
    pending_in_cooling_fees = serializers.FloatField(source='cmp_pending_in_cooling_fees', read_only=True)
    pending_in_cooling_fees_price_per_kg = serializers.FloatField(source='cmp_pending_in_cooling_fees_price_per_kg', read_only=True)
    weight_locked_in_payment_pending_orders_in_kg = serializers.FloatField(
        source='cmp_weight_locked_in_payment_pending_orders_in_kg', read_only=True
    )
    available_weight_in_kg = serializers.FloatField(source='cmp_available_weight_in_kg', read_only=True)

    # Getters
    rel_crop_id = serializers.PrimaryKeyRelatedField(source='crate.produce.crop', read_only=True)
    rel_cooling_unit_id = serializers.PrimaryKeyRelatedField(source='crate.cooling_unit', read_only=True)
    rel_company_id = serializers.PrimaryKeyRelatedField(source='crate.cooling_unit.location.company', read_only=True)
    rel_crate_remaining_shelf_life = serializers.PrimaryKeyRelatedField(source='crate.remaining_shelf_life', read_only=True)
    rel_checkin_movement_code = serializers.CharField(source='crate.produce.checkin.movement.code', read_only=True)

    owned_by_user_id = serializers.PrimaryKeyRelatedField(source='crate.produce.checkin.owned_by_user', read_only=True)
    owned_on_behalf_of_company_id = serializers.PrimaryKeyRelatedField(source='crate.produce.checkin.owned_on_behalf_of_company', read_only=True)

    produce_info = serializers.PrimaryKeyRelatedField(source='crate.produce.additional_info', read_only=True)

    # Custom fields computed in this serializer
    distance = serializers.SerializerMethodField()
    produce_price_per_kg = serializers.SerializerMethodField()

    class Meta:
        model = MarketListedCrate
        fields = [
            'id',
            'created_at',
            'crate_id',
            'currency',
            'produce_price_per_kg',
            'produce_info',

            # Related FKs
            'rel_crop_id',
            'rel_cooling_unit_id',
            'rel_company_id',
            'rel_crate_remaining_shelf_life',
            'rel_checkin_movement_code',

            # Ownership
            'owned_by_user_id',
            'owned_on_behalf_of_company_id',

            # Computed items
            'last_updated_at',
            'pending_in_cooling_fees',
            'pending_in_cooling_fees_price_per_kg',
            'weight_locked_in_payment_pending_orders_in_kg',
            'available_weight_in_kg',

            'distance',
        ]

    def get_produce_price_per_kg(self, obj):
        """
        Returns the produce price per kg. If the attribute is not available on the object,
        retrieves it from the latest related price entry.
        """
        if hasattr(obj, 'produce_price_per_kg') and obj.produce_price_per_kg:
            amount = obj.produce_price_per_kg
        else:
            latest_price_obj = obj.prices.order_by('-created_at').first()
            amount = latest_price_obj.produce_price_per_kg if latest_price_obj else 0
        return quantitize_float(amount, obj.currency)

    def get_distance(self, obj):
        """
        Returns the distance value if it exists and is greater than zero; otherwise, returns None.
        """
        return getattr(obj, 'distance', None) if hasattr(obj, 'distance') and obj.distance > 0 else None


class PaystackAccountSerializer(serializers.ModelSerializer):
    """
    Serializer for PaystackAccount objects.
    """
    class Meta:
        model = PaystackAccount
        fields = [
            'id',
            'created_at',
            'created_by_user',
            'owned_by_user',
            'owned_on_behalf_of_company',
            'account_type',
            'bank_code',
            'country_code',
            'account_number',
            'account_name',
            'paystack_subaccount_code',
        ]