from collections import OrderedDict
from datetime import datetime

from django.contrib.auth.models import Group
from django.db.models import Q
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from base.apps.storage.models import Crop
from base.apps.user.models import (
    BankAccount,
    Company,
    Farmer,
    InvitationUser,
    Operator,
    ServiceProvider,
    User,
)
from base.apps.user.serializers.company import CompanySerializer
from base.apps.user.serializers.user import UserSerializer


class ServiceProviderRegistrationSerializer(serializers.Serializer):
    company = CompanySerializer(many=False)
    user = UserSerializer()

    class Meta:
        model = ServiceProvider
        fields = ("user", "company")

    def validate(self, data):
        # Check Company doesn't exist
        company = data.pop("company")

        if Company.objects.filter(name=company.get("name", None)).exists():
            raise serializers.ValidationError(
                {"company": [_("Company with that name already exists.")]}
            )

        # Check User not exists
        user = data.pop("user")

        phone = user.get("phone")
        if not isinstance(phone, type(None)):
            if User.objects.filter(Q(phone=user.get("phone"))).exists():
                raise serializers.ValidationError({"user": [_("User already exists.")]})

        if User.objects.filter(Q(email=user.get("email", None))).exists():
            raise serializers.ValidationError({"user": [_("User already exists.")]})

        return {"user": user, "company": company}

    def create(self, validated_data):

        user = validated_data.pop("user")
        serialized_user = UserSerializer(
            data=user, context={"request": self.context["request"]}
        )
        if not serialized_user.is_valid():
            raise serializers.ValidationError({"user": [_("Error creating the user")]})
        user_instance = serialized_user.save()

        default_op = OrderedDict(
            [
                ("phone", ""),
                ("email", ""),
                ("password", "password"),
                ("first_name", "Default"),
                ("last_name", "Operator"),
            ]
        )

        serialized_op = UserSerializer(
            data=default_op, context={"request": self.context["request"]}
        )
        if not serialized_op.is_valid():
            raise serializers.ValidationError({"user": [_("Error creating the user")]})
        op_instance = serialized_op.save()

        unknown_farmer = OrderedDict(
            [
                ("phone", ""),
                ("email", ""),
                ("password", "password"),
                ("first_name", "User without a phone"),
                ("last_name", ""),
            ]
        )

        serialized_farmer = UserSerializer(
            data=unknown_farmer, context={"request": self.context["request"]}
        )
        if not serialized_farmer.is_valid():
            raise serializers.ValidationError({"user": [_("Error creating the user")]})
        farmer_instance = serialized_farmer.save()

        data = self.context["request"].data
        required_fields = ["bank_name", "account_name", "account_number"]

        bank_instance_created = None
        if all(field in data for field in required_fields):
            bank_instance_created = BankAccount.objects.create(
                bank_name=data["bank_name"],
                account_name=data["account_name"],
                account_number=data["account_number"],
            )

        company = validated_data.pop("company")
        company_instance = Company.objects.create(
            name=company["name"],
            country=company["country"],
            currency=company["currency"],
            bank_account=bank_instance_created,
            ML4_market=company["country"] == "IN" or company["country"] == "NG",
            date_joined=datetime.now().astimezone(),
        )

        # Company.objects.filter(id=company_instance.id).update(currency = company_instance.country.alpha3)
        crops = Crop.objects.all().values_list("id", flat=True)
        company_instance.crop.set(crops)

        service_provider_role = Group.objects.get(name="ServiceProvider")
        service_provider_role.user_set.add(user_instance)

        op_role = Group.objects.get(name="Operator")
        op_role.user_set.add(op_instance)

        operator = Operator.objects.create(user=op_instance, company=company_instance)

        Farmer.objects.create(user=farmer_instance, created_by=operator, is_unknown=True)

        instance = ServiceProvider.objects.create(
            **validated_data, user=user_instance, company=company_instance
        )
        return instance


class ServiceProviderRegistrationWithInvitationSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    password = serializers.CharField(min_length=8, write_only=True)
    code = serializers.CharField(write_only=True)
    user = UserSerializer(read_only=True)

    def validate(self, data):
        # Check User not exists
        email = data.pop("email")
        code = data.pop("code")

        # Check Invitation exists and it's correct
        invitation = InvitationUser.objects.filter(code=code).last()

        if not invitation:
            raise serializers.ValidationError(
                {"invitation": [_("The code introduced is incorrect")]}
            )

        if User.objects.filter(
            Q(phone=str(invitation.phone)) | Q(email=email)
        ).exists():
            raise serializers.ValidationError({"user": [_("User already exists.")]})

        # Check Invitation user type is correct
        if invitation.user_type != 1:
            raise serializers.ValidationError(
                {"invitation": [_("The invitation type is incorrect.")]}
            )

        # Check Invitation sender is correct
        if not invitation.sender.service_provider:
            raise serializers.ValidationError(
                {"invitation": [_("The invitation is incorrect")]}
            )

        # Everything went right, so the invitation will expire
        invitation.expiration_date = timezone.now()
        invitation.save()

        user = OrderedDict(
            {
                "email": email,
                "phone": str(invitation.phone),
                "first_name": data.pop("first_name"),
                "last_name": data.pop("last_name"),
                "password": data.pop("password"),
                "gender": self.context["request"].data["gender"],
            }
        )

        return {"user": user, "company": invitation.sender.service_provider.company}

    @atomic
    def create(self, validated_data):
        company = validated_data.pop("company")
        company_instance = get_object_or_404(Company, id=company.id)

        user = validated_data.pop("user")
        serialized_user = UserSerializer(
            data=user, context={"request": self.context["request"]}
        )
        if not serialized_user.is_valid():
            raise serializers.ValidationError({"user": [_("Error creating the user")]})
        user_instance = serialized_user.save()

        service_provider_role = Group.objects.get(name="ServiceProvider")
        service_provider_role.user_set.add(user_instance)

        instance = ServiceProvider.objects.create(
            user=user_instance, company=company_instance
        )
        return instance
