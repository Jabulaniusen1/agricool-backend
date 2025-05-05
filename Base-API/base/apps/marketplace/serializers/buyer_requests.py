import re

from rest_framework import serializers

from base.apps.marketplace.models import MarketListedCrate, OrderPickupDetails
from base.apps.storage.models import Crate

"""
Buyer-related serializers for marketplace operations.

These serializers handle query parameters, cart item additions/updates,
coupon applications, and pickup detail settings for buyer requests.
"""


class BuyerMarketListingQueryParamsSerializer(serializers.Serializer):
    """
    Serializer for querying marketplace listings based on location, sorting,
    filtering by cooling unit IDs, maximum distance, and pagination.
    """
    location = serializers.CharField(
        required=True,
        help_text="Latitude,Longitude (e.g., '12.34,56.78')"
    )
    sort_by = serializers.ChoiceField(
        choices=[
            ('nearby-me', 'Nearby'),
            ('price-asc', 'Price Asc'),
            ('price-desc', 'Price Desc')
        ],
        required=False,
        default='nearby-me'
    )
    filter_by_cooling_units_ids = serializers.CharField(
        required=False,
        default='',
        help_text="Comma-separated list of cooling unit IDs"
    )
    filter_by_max_distance_in_km = serializers.FloatField(
        required=False,
        default=None,
        help_text="Maximum distance in kilometers"
    )
    page = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1
    )
    items_per_page = serializers.IntegerField(
        required=False,
        default=50,
        min_value=10
    )

    def validate_location(self, value):
        """
        Validate that the location string is in the correct "lat,lng" format.
        """
        try:
            lat, lng = map(float, value.split(','))
        except ValueError:
            raise serializers.ValidationError("Invalid location format. Expected format: 'lat,lng'")
        return lat, lng

    def validate_filter_by_cooling_units_ids(self, value):
        """
        Validate that the cooling unit IDs are provided as a comma-separated string of integers.
        """
        if value:
            try:
                return list(map(int, value.split(',')))
            except ValueError:
                raise serializers.ValidationError("Invalid cooling unit IDs format. Expected comma-separated integers")
        return []

    def validate(self, data):
        """
        Ensure that pagination and sorting parameters have default values if not provided.
        """
        if data.get('page') is None:
            data['page'] = self.fields['page'].initial

        if data.get('items_per_page') is None:
            data['items_per_page'] = self.fields['items_per_page'].initial

        if data.get('sort_by') is None:
            data['sort_by'] = self.fields['sort_by'].initial

        return data


class BuyerAddItemToCartRequestSerializer(serializers.Serializer):
    """
    Serializer for adding an item to the cart.
    It includes the strategy for updating (replace/increase/decrease), the crate ID,
    and the ordered produce weight in kilograms.
    """
    update_strategy = serializers.ChoiceField(
        choices=[
            ('replace', 'Replace'),
            ('increase', 'Increase'),
            ('decrease', 'Decrease')
        ],
        required=False,
        default='replace'
    )
    crate_id = serializers.IntegerField(required=True, min_value=1)
    ordered_produce_weight = serializers.FloatField(
        required=True,
        help_text="Ordered produce weight in kilograms",
        min_value=0.1
    )

    class Meta:
        fields = ['market_listed_crate_id', 'ordered_produce_weight']  # List the fields to be validated/serialized

    def validate_ordered_produce_weight(self, value):
        """
        Validate that the ordered produce weight has at most one decimal place.
        """
        value_str = str(value)
        if not re.match(r'^\d+(\.\d{1})?$', value_str):
            raise serializers.ValidationError("Ordered produce weight must have at most one decimal place.")
        return value

    def validate_crate_id(self, value):
        """
        Validate that the crate exists and that it has an active market listing.
        """
        try:
            crate = Crate.objects.get(id=value)
        except Crate.DoesNotExist:
            raise serializers.ValidationError("Crate does not exist.")

        if not MarketListedCrate.objects.filter(crate=crate, delisted_at=None).exists():
            raise serializers.ValidationError("Crate does not have an active market listing.")

        return value


class BuyerUpdateItemInCartRequestSerializer(serializers.Serializer):
    """
    Serializer for updating an existing cart item, specifically the ordered produce weight.
    """
    ordered_produce_weight = serializers.FloatField(
        required=True,
        help_text="Ordered produce weight in kilograms",
        min_value=0.1
    )

    class Meta:
        fields = ['ordered_produce_weight']

    def validate_ordered_produce_weight(self, value):
        """
        Validate that the ordered produce weight has at most one decimal place.
        """
        value_str = str(value)
        if not re.match(r'^\d+(\.\d{1})?$', value_str):
            raise serializers.ValidationError("Ordered produce weight must have at most one decimal place.")
        return value


class BuyerApplyOrClearCouponRequestSerializer(serializers.Serializer):
    """
    Serializer for applying or clearing a coupon code on an order.
    """
    coupon_code = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="Coupon code",
        max_length=40
    )

    class Meta:
        fields = ['coupon_code']

    def validate_coupon_code(self, value):
        """
        Validate the coupon code by stripping whitespace, ensuring it's not empty,
        and removing any non-alphanumeric characters while converting to uppercase.
        """
        if value.strip() == '':
            raise serializers.ValidationError("Coupon code cannot be empty.")
        # Remove any non-alphanumeric characters and convert to uppercase
        return re.sub(r'[^A-Za-z0-9]', '', value.strip().upper())


class BuyerSetPickupDetails_PickUpDetailsSerializer(serializers.Serializer):
    """
    Serializer for individual pickup detail settings, including the cooling unit ID and the pickup method.
    """
    cooling_unit_id = serializers.IntegerField(required=True, min_value=1)
    pickup_method = serializers.ChoiceField(
        choices=OrderPickupDetails.PickUpMethod.choices,
        write_only=True
    )
    # TODO: Validate that cooling_unit_id corresponds to one of the order items in the cart.


class BuyerSetPickupDetailsRequestSerializer(serializers.Serializer):
    """
    Serializer for setting pickup details on an order.
    Expects a list of pickup detail objects.
    """
    pickup_details = serializers.ListField(child=BuyerSetPickupDetails_PickUpDetailsSerializer())

    class Meta:
        fields = ['pickup_details']
