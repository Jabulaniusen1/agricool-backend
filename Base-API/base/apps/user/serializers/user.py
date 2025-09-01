import uuid

from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from base.apps.storage.models import CoolingUnit
from base.apps.user.models import Operator, ServiceProvider, User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(min_length=8, write_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "phone",
            "email",
            "gender",
            "password",
            "first_name",
            "last_name",
            "last_login",
            "language",
            "is_email_public",
            "is_phone_public",
        )
        extra_kwargs = {
            "password": {"write_only": True},
            "username": {"read_only": True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")

        if not request:
            return data

        user = request.user

        # If public, always allow
        if not instance.is_phone_public and not instance.is_email_public:
            if not user.is_authenticated:
                data.pop("phone", None)
                data.pop("email", None)
            else:
                # Check if it's the user's own profile
                if instance == user:
                    return data

                # Check Operator or Employee logic
                operator = Operator.objects.filter(user=user).first()
                employee = ServiceProvider.objects.filter(user=user).first()
                company_id = (
                    operator.company_id
                    if operator
                    else (employee.company_id if employee else None)
                )

                if company_id:
                    # Check if the linked Farmer belongs to the company via cooling units
                    farmer = getattr(instance, "farmer", None)
                    if farmer and not farmer.companies.filter(id=company_id).exists():
                        data.pop("phone", None)
                        data.pop("email", None)
                else:
                    data.pop("phone", None)
                    data.pop("email", None)

        else:
            if not instance.is_phone_public:
                data.pop("phone", None)
            if not instance.is_email_public:
                data.pop("email", None)

        return data

    @atomic
    def create(self, validated_data):
        password = validated_data.pop("password", None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.username = uuid.uuid4().hex[:30]
        instance.save()
        return instance

    def update(self, instance, validated_data):
        # get the cooling units sent with the user
        cooling_units = self.context["request"].data["cooling_units"]

        if cooling_units != None:
            # get the cooling units the operator is assigned to already
            operator_cooling_units = CoolingUnit.objects.filter(
                operators=instance
            ).values("id")

            # if one of the cooling unit sent with the request is not already assigned to the op, assign op to it
            for cu in cooling_units:
                if instance not in CoolingUnit.objects.get(id=cu).operators.all():
                    CoolingUnit.objects.get(id=cu).operators.add(instance.id)

            # if a cooling unit assigned to the op is not part of the cooling units sent in the request, remove op from it
            for op_cu in operator_cooling_units:
                if op_cu["id"] not in cooling_units:
                    CoolingUnit.objects.get(id=op_cu["id"]).operators.remove(
                        instance.id
                    )

        return super().update(instance, validated_data)


class PublicUserSerializer(UserSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["phone"] = str(instance.phone) if instance.phone else None
        data["email"] = str(instance.email) if instance.email else None
        return data
