import random
import string

from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from base.apps.storage.models import CoolingUnit
from base.apps.user.models import Company, Farmer, Operator, User
from base.apps.user.serializers.user import UserSerializer

class FarmerSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Farmer
        fields = (
            "id",
            "user",
            "birthday",
            "parent_name",
            "country",
            "user_code",
            "companies",
            "cooling_units",
        )

    def get_user(self, obj):
        context = self.context
        return UserSerializer(obj.user, context=context).data

    def validate(self, data):
        # Check User not exists
        if "updateUser" in self.context["request"].data:
            return {
                "parent_name": data.pop("parent_name"),
                "country": data.pop("country"),
                "update_user": True,
            }

        if "update_cooling_units" in self.context["request"].data:
            return {
                "cooling_unit_id": self.context["request"].data["cooling_unit_id"],
                "update_user": False,
            }

        if "update_companies" in self.context["request"].data:
            return {
                "company_id": self.context["request"].data["company_id"],
                "update_user": False,
            }

        if "delete_company" in self.context["request"].data:
            return {
                "delete_company_id": self.context["request"].data["company_id"],
                "update_user": False,
            }

        user = data.pop("user")
        parent_name = data.pop("parent_name")
        createUser = self.context["request"].data["createUser"]

        if createUser:
            if Farmer.objects.filter(
                user__phone=user.get("phone", None), smartphone=True
            ).exists():
                raise serializers.ValidationError(
                    {"user": [_("User with this phone number already exists.")]}
                )
            return {
                "user": user,
                "parent_name": parent_name,
                "createUser": createUser,
            }
        else:
            if Farmer.objects.filter(user__phone=user.get("phone", None)).exists():
                raise serializers.ValidationError(
                    {"user": [_("User with this phone number already exists.")]}
                )
            return {
                "user": user,
                "parent_name": parent_name,
                "createUser": createUser,
            }

    def update(self, instance, validated_data):
        update_user = validated_data.pop("update_user")
        if not update_user:
            if "cooling_unit_id" in validated_data:
                cooling_units = instance.cooling_units
                cooling_unit_id = validated_data.pop("cooling_unit_id")
                if not cooling_units.filter(pk=cooling_unit_id).exists():
                    cooling_unit = CoolingUnit.objects.get(id=cooling_unit_id)
                    cooling_units.add(cooling_unit)
                    company = cooling_unit.location.company
                    if not instance.companies.filter(pk=company.id).exists():
                        instance.companies.add(company)
            elif "delete_company_id" in validated_data:
                company_id = validated_data.pop("delete_company_id")
                if instance.companies.filter(pk=company_id).exists():
                    company = Company.objects.get(id=company_id)
                    instance.companies.remove(company)
                    cooling_units = instance.cooling_units.filter(
                        location__company_id=company_id
                    )
                    for cu in cooling_units:
                        instance.cooling_units.remove(cu)
            else:
                companies = instance.companies
                company_id = validated_data.pop("company_id")
                if not companies.filter(pk=company_id).exists():
                    company = Company.objects.get(id=company_id)
                    instance.companies.add(company)

        return super().update(instance, validated_data)

    def create(self, validated_data):
        user = validated_data.pop("user")
        if "language" in user.__dict__ and user["language"] == "":
            user["language"] = "en"
        createUser = validated_data.pop("createUser")
        serialized_user = UserSerializer(
            data=user, context={"request": self.context["request"]}
        )
        if not serialized_user.is_valid():
            raise serializers.ValidationError({"user": [_("Error creating the user")]})

        if createUser:
            try:
                farmer_instance = Farmer.objects.get(
                    user__phone=user.get("phone", None)
                )
                user_instance = User.objects.get(phone=user.get("phone", None))
                user_instance.gender = user["gender"]
                user_instance.set_password(user["password"])
                user_instance.first_name = user["first_name"]
                user_instance.last_name = user["last_name"]
                user_instance.language = user["language"]
                user_instance.save()
            except:
                user_instance = serialized_user.save()
                farmer_instance = Farmer.objects.create(
                    **validated_data, user=user_instance
                )

            farmer_role = Group.objects.get(name="Farmer")
            farmer_role.user_set.add(user_instance)
            unique_user_code = self.context["request"].data.get("user_code")

            if unique_user_code is None:
                unique_user_code = "".join(
                    random.choices(string.ascii_uppercase + string.digits, k=8)
                )
            #     if the provided user_code already exists, generate a new one
            while Farmer.objects.filter(user_code=unique_user_code).exists():
                unique_user_code = "".join(
                    random.choices(string.ascii_uppercase + string.digits, k=8)
                )

            farmer_instance.smartphone = True
            farmer_instance.country = self.context["request"].data["user"]["country"]
            farmer_instance.user_code = unique_user_code
            farmer_instance.save()
        else:
            user_instance = serialized_user.save()
            farmer_instance = Farmer.objects.create(
                **validated_data,
                user=user_instance,
                created_by=Operator.objects.get(user=self.context["request"].user),
                smartphone=False,
            )
        return farmer_instance


class FarmerWithPublicUserSerializer(FarmerSerializer):
    from base.apps.user.serializers.user import PublicUserSerializer
    user = PublicUserSerializer()
