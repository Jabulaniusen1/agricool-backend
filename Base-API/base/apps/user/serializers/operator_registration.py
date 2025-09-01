from collections import OrderedDict

from django.contrib.auth.models import Group
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from base.apps.user.models import Company, InvitationUser, Operator, User
from base.apps.user.serializers.user import UserSerializer


class OperatorRegistrationWithInvitationSerializer(serializers.Serializer):
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    password = serializers.CharField(min_length=8, write_only=True)
    code = serializers.CharField(write_only=True)
    user = UserSerializer(read_only=True)

    def validate(self, data):
        code = data.pop("code")

        # Check Invitation exists and it's correct
        invitation = InvitationUser.objects.filter(code=code).last()

        cooling_units = invitation.cooling_units.all()

        if not invitation:
            raise serializers.ValidationError(
                {"invitation": [_("The code introduced is incorrect")]}
            )

        # Check User not exists
        if User.objects.filter(phone=str(invitation.phone)).exists():
            raise serializers.ValidationError({"user": [_("User already exists.")]})

        # Check Invitation is not expired
        if invitation.expiration_date <= timezone.now():
            raise serializers.ValidationError(
                {"invitation": [_("The invitation is incorrect.")]}
            )

        # Check Invitation user type is correct
        if invitation.user_type != 2:
            raise serializers.ValidationError(
                {"invitation": [_("The invitation type is incorrect.")]}
            )

        # Check Invitation code is correct
        if code != invitation.code:
            raise serializers.ValidationError(
                {"invitation": [_("The code introduced is incorrect.")]}
            )

        # Everything went right, so the invitation will expire
        invitation.expiration_date = timezone.now()
        invitation.save()

        user = OrderedDict(
            {
                "phone": str(invitation.phone),
                "first_name": data.pop("first_name"),
                "last_name": data.pop("last_name"),
                "password": data.pop("password"),
                "gender": self.context["request"].data["gender"],
            }
        )

        return {
            "user": user,
            "company": invitation.sender.service_provider.company,
            "cooling_units": cooling_units,
        }

    @atomic
    def create(self, validated_data):
        company = validated_data.pop("company")
        cooling_units = validated_data.pop("cooling_units")
        company_instance = get_object_or_404(Company, id=company.id)

        user = validated_data.pop("user")
        serialized_user = UserSerializer(
            data=user, context={"request": self.context["request"]}
        )
        if not serialized_user.is_valid():
            raise serializers.ValidationError({"user": [_("Error creating the user")]})
        user_instance = serialized_user.save()

        operator_role = Group.objects.get(name="Operator")
        operator_role.user_set.add(user_instance)

        instance = Operator.objects.create(
            **validated_data, user=user_instance, company=company_instance
        )
        for cu in cooling_units:
            cu.operators.add(instance.user.id)

        return instance
