import re

from rest_framework import serializers

from base.apps.marketplace.models import PaystackAccount

##
# Seller related serializers
##

# --- Coupons --- #

class SellerRegisterNewCouponRequestSerializer(serializers.Serializer):
    """
    Serializer for registering a new coupon by a seller.
    Validates the coupon code and discount percentage.
    """
    code = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="Coupon code",
        max_length=40
    )
    discount_percentage = serializers.FloatField(
        required=True,
        help_text="Discount percentage (between 0 and 1)",
        min_value=0,
        max_value=1
    )

    class Meta:
        fields = ['code', 'discount_percentage']

    def validate_code(self, value):
        """
        Validate the coupon code by stripping whitespace, ensuring
        it's not empty, removing non-alphanumeric characters, and converting it to uppercase.
        """
        if value.strip() == '':
            raise serializers.ValidationError("Coupon code cannot be empty.")
        return re.sub(r'[^A-Za-z0-9]', '', value.strip().upper())


# --- Listings --- #

class SellerListingUpdateRequestSerializer(serializers.Serializer):
    """
    Serializer for sellers to update their listing details for multiple crates.
    Validates the list of crate IDs and the price per kilogram of produce.
    """
    crate_ids = serializers.ListField(
        child=serializers.IntegerField(required=True, help_text="Crate ID", min_value=1),
        required=True,
        help_text="List of Crate IDs"
    )
    produce_price_per_kg = serializers.FloatField(
        required=True,
        help_text="Price per kilogram of produce"
    )

    class Meta:
        fields = ['produce_price_per_kg', 'crate_ids']

    def validate_produce_price_per_kg(self, value):
        """
        Validate that the produce price per kilogram is non-negative.
        """
        if value < 0:
            raise serializers.ValidationError("Price per kg must be non-negative.")
        return value


# --- Paystack Account --- #

class SellerAttachPaystackAccountRequestSerializer(serializers.Serializer):
    """
    Serializer for attaching a Paystack account to a seller profile.
    Validates bank details and account information.
    """
    company_id = serializers.IntegerField(
        required=False,
        help_text="Company ID (if applicable)",
        min_value=1
    )
    account_type = serializers.ChoiceField(
        choices=PaystackAccount.AccountType.choices,
        required=True,
        help_text="Account type"
    )
    bank_code = serializers.RegexField(
        regex=re.compile(r'^[A-Z0-9]{1,9}$'),
        help_text="Bank code (alphanumeric, 1-9 characters)"
    )
    country_code = serializers.RegexField(
        regex=re.compile(r'^[A-Z]{2}$'),
        help_text="Country code (2 uppercase letters)"
    )
    account_number = serializers.RegexField(
        regex=re.compile(r'^[0-9]{6,30}$'),
        help_text="Account number (6 to 30 digits)"
    )
    account_name = serializers.CharField(
        max_length=100,
        help_text="Account name"
    )

    class Meta:
        fields = [
            'company_id',
            'account_type',
            'bank_code',
            'country_code',
            'account_number',
            'account_name'
        ]

    # If you need custom validation on account_type, you can uncomment and modify the method below.
    # def validate_account_type(self, value):
    #     for account_type in PaystackAccount.AccountType.choices:
    #         if account_type[1] == value:
    #             return account_type
    #     raise serializers.ValidationError("Invalid account type.")
