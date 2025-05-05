import re

from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from base.apps.marketplace.models import PaystackAccount


class CompanyCreateDeliveryContactRequestSerializer(serializers.Serializer):
    """
    Serializer for creating a company's delivery contact.
    Validates the delivery company name, contact name, and phone number.
    """
    delivery_company_name = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="Delivery Company Name",
        max_length=255
    )
    contact_name = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="Contact Name",
        max_length=255
    )
    phone = PhoneNumberField(
        required=True,
        help_text="Contact phone"
    )

    class Meta:
        fields = ['delivery_company_name', 'contact_name', 'phone']


class CompanySetupUsersFirstPaystackBankAccountRequestSerializer(serializers.Serializer):
    """
    Serializer for setting up a user's first Paystack bank account.
    Validates fields such as account type, bank code, country code, account number, and account name.
    """
    owned_by_user_id = serializers.IntegerField(
        required=True,
        help_text="User ID"
    )
    account_type = serializers.ChoiceField(
        choices=PaystackAccount.AccountType.choices,
        required=True,
        help_text="Account type"
    )
    bank_code = serializers.RegexField(re.compile(r'^[A-Z0-9]{1,9}$')) # TODO: base this on a list of dynamic choices by using the Paystack API / list of banks
    country_code = serializers.RegexField(re.compile(r'^[A-Z]{2}$'))
    account_number = serializers.RegexField(re.compile(r'^[0-9]{6,30}$'))
    account_name = serializers.CharField(
        max_length=100,
        help_text="Account name"
    )

    class Meta:
        fields = [
            'account_type',
            'bank_code',
            'country_code',
            'account_number',
            'account_name'
        ]


class CompanySetupEligibilityCheckRequestSerializer(serializers.Serializer):
    """
    Serializer for checking a company's or user's eligibility.
    Accepts lists of company IDs and/or user IDs.
    """
    company_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Company IDs",
        allow_empty=False
    )
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="User IDs",
        allow_empty=False
    )

    class Meta:
        fields = [
            'company_ids',
            'user_ids',
        ]
