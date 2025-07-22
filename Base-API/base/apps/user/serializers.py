import base64
import os
import random
import string
import uuid
from collections import OrderedDict
from datetime import datetime

from django.contrib.auth.models import Group
from django.db.models import Q
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from base.apps.marketplace.models import MarketListedCratePrice
from base.apps.operation.models import Checkin, Checkout
from base.apps.storage.models import (
    CoolingUnit,
    CoolingUnitCrop,
    Crop,
    Pricing,
    Produce,
)

from .models import (
    BankAccount,
    Company,
    Farmer,
    FarmerSurvey,
    FarmerSurveyCommodity,
    GenericUserCode,
    InvitationUser,
    Notification,
    Operator,
    ServiceProvider,
    User,
)


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

class CompanySerializer(CountryFieldMixin, serializers.ModelSerializer):
    has_cooling_units = serializers.SerializerMethodField()
    bank_details = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = "__all__"

    def get_has_cooling_units(self, instance):
        if CoolingUnit.objects.filter(location__company=instance, deleted=False):
            return True
        else:
            return False

    def get_bank_details(self, instance):
        if instance.bank_account:
            return {
                "id": instance.bank_account.id,
                "bank_name": instance.bank_account.bank_name,
                "account_name": instance.bank_account.account_name,
                "account_number": instance.bank_account.account_number,
            }

    def create(self, validated_data):
        if validated_data["country"] == "IN" or validated_data["country"] == "NG":
            ml4market = True
        else:
            ml4market = False

        companyInstance = Company.objects.create(**validated_data, ML4_market=ml4market)

        return companyInstance

    def update(self, instance, validated_data):

        if instance.country != validated_data["country"]:
            if "crop" in validated_data:
                validated_data.pop("crop")
            crops = (
                Crop.objects.filter(countryRelated__country=validated_data["country"])
                .exclude(name="Other")
                .values_list("id", flat=True)
            )
            if validated_data["country"] == "IN" or validated_data["country"] == "NG":
                validated_data["ML4_market"] = True
            else:
                validated_data["ML4_market"] = False

            # Updates company's cooling units to have all crops of the country active
            cooling_units = CoolingUnit.objects.filter(location__company=instance)
            for cu in cooling_units:
                # Disable all current crops from the cooling unit
                CoolingUnitCrop.objects.filter(cooling_unit=cu).exclude(
                    crop__name="Other"
                ).update(active=False)

                # If a crop in the request isn't already attached to this cooling unit, add it with the default price of the other crops
                first_unit_pricing = CoolingUnitCrop.objects.filter(
                    cooling_unit=cu
                ).first()
                print("first_unit_pricing", first_unit_pricing)
                pricing_instance = (
                    first_unit_pricing.pricing if first_unit_pricing else None
                )

                for crop in crops:
                    cu_crop = CoolingUnitCrop.objects.filter(
                        crop_id=crop, cooling_unit=cu
                    )
                    if cu_crop:
                        CoolingUnitCrop.objects.filter(
                            crop_id=crop, cooling_unit=cu
                        ).update(active=True)
                    # only create a new entry if pricing_instance is not None and the crop is not already attached to the cooling unit
                    elif pricing_instance:
                        new_pricing_instance = Pricing.objects.create(
                            pricing_type=pricing_instance.pricing_type,
                            fixed_rate=pricing_instance.fixed_rate,
                            daily_rate=pricing_instance.daily_rate,
                        )
                        CoolingUnitCrop.objects.create(
                            crop_id=crop,
                            cooling_unit=cu,
                            pricing=new_pricing_instance,
                            active=True,
                        )
        else:
            crops = validated_data.pop("crop")

        instance.crop.set(crops)

        data = self.context["request"].data
        required_fields = ["bank_name", "account_name", "account_number"]

        bank_account_id = instance.bank_account.id if instance.bank_account else None

        if all(field in data for field in required_fields):
            bank_account_data = {
                "bank_name": data["bank_name"],
                "account_name": data["account_name"],
                "account_number": data["account_number"],
            }

            try:
                # Try to get the existing bank account by ID
                bank_account = BankAccount.objects.get(id=bank_account_id)
                # Update the bank account with new data
                for key, value in bank_account_data.items():
                    setattr(bank_account, key, value)
                bank_account.save()
            except BankAccount.DoesNotExist:
                # Create a new bank account if not found
                bank_account = BankAccount.objects.create(**bank_account_data)
                # Link the bank account to the instance
                instance.bank_account = bank_account

        return super().update(instance, validated_data)


class ServiceProviderSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False)
    user = UserSerializer()

    class Meta:
        model = ServiceProvider
        fields = ("id", "user", "company")


class OperatorSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False)
    user = UserSerializer()
    cooling_units = serializers.SerializerMethodField()

    class Meta:
        model = Operator
        fields = ("id", "user", "company", "cooling_units")

    def get_cooling_units(self, instance):
        cooling_units = CoolingUnit.objects.filter(
            operators=instance.user, deleted=False
        ).values_list("id", flat=True)
        return cooling_units


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
    user = PublicUserSerializer()

class InvitationUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvitationUser
        fields = ("phone", "code", "user_type", "cooling_units", "expiration_date")
        extra_kwargs = {
            "code": {"read_only": True},
            "expiration_date": {"read_only": True},
        }

    @atomic
    def create(self, validated_data):
        InvitationUser.clear_invitations(phone=validated_data["phone"])

        invite = InvitationUser.send_invitation(
            phone=validated_data["phone"],
            user=self.context["request"].user,
            user_type=validated_data["user_type"],
            cooling_units=validated_data["cooling_units"],
        )

        return invite

    def get_has_accepted(self, instance):
        if User.objects.filter(phone=instance.phone):
            return True

        return False


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

        Farmer.objects.create(user=farmer_instance, created_by=operator, isUnknown=True)

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


class OperatorRegistrationWithInvitationSerializer(serializers.Serializer):
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    password = serializers.CharField(min_length=8, write_only=True)
    code = serializers.CharField(write_only=True)
    user = UserSerializer(read_only=True)

    # invitation = InvitationUserSerializer(read_only=True)

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


class ServiceProviderLoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):

        sp = ServiceProvider.objects.filter(
            Q(user__phone__iexact=attrs[self.username_field])
            | Q(user__email__iexact=attrs[self.username_field])
            # | Q(user__username__iexact=attrs[self.username_field])
        ).first()

        if not sp:
            print("Service Provider Login Error", attrs[self.username_field])
            raise serializers.ValidationError({"user": [_("User not exists")]})
        attrs[self.username_field] = sp.user.username
        data = super().validate(attrs)

        company = Company.objects.get(id=sp.company.id)
        company_serializer = CompanySerializer(company)
        if sp.user.language is not self.initial_data["language"]:
            sp.user.language = self.initial_data["language"]
            sp.user.save()
        refresh = self.get_token(self.user)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        # Add extra responses here
        data["user"] = {
            "id": sp.user.id,
            "first_name": sp.user.first_name,
            "last_name": sp.user.last_name,
            "email": sp.user.email,
            "gender": sp.user.gender,
            "phone": str(sp.user.phone),
            "last_login": str(sp.user.last_login),
        }
        data["role"] = "Service Provider"
        data["company"] = company_serializer.data
        return data


class OperatorLoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        op = Operator.objects.filter(
            user__phone__iexact=attrs[self.username_field]
            # | Q(user__username__iexact=attrs[self.username_field])
        ).first()
        if not op:
            print("Operator Login Error", attrs[self.username_field])
            raise serializers.ValidationError({"user": [_("User not exists")]})
        attrs[self.username_field] = op.user.username
        data = super().validate(attrs)
        if op.user.language is not self.initial_data["language"]:
            op.user.language = self.initial_data["language"]
            op.user.save()
        company = Company.objects.get(id=op.company.id)
        company_serializer = CompanySerializer(company)

        refresh = self.get_token(self.user)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        # Add extra responses here
        data["user"] = {
            "id": op.user.id,
            "first_name": op.user.first_name,
            "last_name": op.user.last_name,
            "gender": op.user.gender,
            "phone": str(op.user.phone),
            "last_login": str(op.user.last_login),
        }
        data["role"] = "Operator"
        data["company"] = company_serializer.data
        return data


class FarmerLoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # In the front, send username as FIRST_NAME_STRING+PARENT_NAME_STRING for this to work
        # farmer_username = attrs[self.username_field].split('+')
        # f = Farmer.objects.filter(
        #     Q(user__first_name__iexact=farmer_username[0])
        #     | Q(parent_name__iexact=farmer_username[1])
        #     # | Q(username__iexact=farmer_username[0])
        #     ).first()
        phone_number = attrs[self.username_field]
        f = Farmer.objects.filter(user__phone__iexact=phone_number).first()
        if not f:
            print("Farmer Login Error", attrs[self.username_field])
            raise serializers.ValidationError({"user": [_("User not exists")]})
        attrs[self.username_field] = f.user.username
        data = super().validate(attrs)

        refresh = self.get_token(self.user)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        # Add extra responses here
        data["user"] = {
            "id": f.user.id,
            "first_name": f.user.first_name,
            "last_name": f.user.last_name,
            "gender": f.user.gender,
            "phone": str(f.user.phone),
            "last_login": str(f.user.last_login),
        }
        data["parent_name"] = f.parent_name
        data["role"] = "Farmer"
        return data


class FarmerSurveySerializer(serializers.ModelSerializer):
    co = serializers.SerializerMethodField()

    class Meta:
        model = FarmerSurvey
        fields = "__all__"

    def create(self, validated_data):
        commodities = self.context["commodities"]

        farmer_survey_instance = FarmerSurvey.objects.create(
            **validated_data,
            date_filled_in=datetime.now().astimezone(),
            date_last_modified=datetime.now().astimezone(),
        )
        for crop_item in commodities:
            if crop_item["crop_id"] != "":
                FarmerSurveyCommodity.objects.create(
                    farmer_survey_id=farmer_survey_instance.id,
                    crop_id=crop_item["crop_id"],
                    average_price=crop_item["average_price"],
                    unit=crop_item["unit"],
                    reason_for_loss=crop_item["reason_for_loss"],
                    kg_in_unit=crop_item["kg_in_unit"],
                    quantity_total=crop_item["quantity_total"],
                    quantity_self_consumed=crop_item["quantity_self_consumed"],
                    quantity_sold=crop_item["quantity_sold"],
                    quantity_below_market_price=crop_item[
                        "quantity_below_market_price"
                    ],
                    average_season_in_months=crop_item["average_season_in_months"],
                    currency=crop_item["currency"],
                    date_filled_in=datetime.now().astimezone(),
                    date_last_modified=datetime.now().astimezone(),
                )
        return farmer_survey_instance

    def get_co(self, instance):
        co = FarmerSurveyCommodity.objects.filter(farmer_survey=instance.id).values()
        return co


class FarmerSurveyCommoditySerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerSurveyCommodity
        fields = "__all__"


class NotificationSerializer(serializers.ModelSerializer):
    cooling_unit_name = serializers.SerializerMethodField()
    crates = serializers.SerializerMethodField()
    movement_code = serializers.SerializerMethodField()
    market_listing = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = "__all__"

    def get_market_listing(self, instance):
        try:
            if (
                instance.event_type
                == Notification.NotificationType.LISTING_PRICE_UPDATED
            ):
                market_listing_price = MarketListedCratePrice.objects.get(
                    id=instance.specific_id
                )

                return {
                    "price_per_kg": market_listing_price.produce_price_per_kg,
                    "currency": market_listing_price.market_listed_crate.currency,
                }

            return None
        except:
            return None

    def get_cooling_unit_name(self, instance):
        try:
            cu = None

            if instance.event_type == "SENSOR_ERROR":
                cu = CoolingUnit.objects.get(id=instance.specific_id).name

            if (
                instance.event_type
                == Notification.NotificationType.LISTING_PRICE_UPDATED
            ):
                cu = (
                    CoolingUnit.objects.filter(
                        crate_cooling_unit__market_listed_crates__prices__id=instance.specific_id
                    )
                    .first()
                    .name
                )

            return cu
        except:
            return None

    def get_crates(self, instance):
        try:
            produce = None

            if (
                instance.event_type == "TIME_TO_PICKUP"
                or instance.event_type == "FARMER_SURVEY"
            ):
                produce = Produce.objects.get(id=instance.specific_id)

            elif instance.event_type == "MARKET_SURVEY":
                produce = Produce.objects.filter(
                    crates__partial_checkouts__checkout_id=instance.specific_id
                ).first()

            elif instance.event_type == "CHECKOUT_EDITED":
                produce = Produce.objects.filter(
                    checkin_id=instance.specific_id
                ).first()

            elif instance.event_type == "ORDER_REQUIRES_MOVEMENT":
                produce = Produce.objects.filter(
                    checkin__movement_id=instance.specific_id
                ).first()

            elif (
                instance.event_type
                == Notification.NotificationType.LISTING_PRICE_UPDATED
            ):
                produce = Produce.objects.filter(
                    crates__market_listed_crates__prices__id=instance.specific_id
                ).first()

            if produce:
                owned_by_user = produce.checkin.owned_by_user

                # Attempt to access the Farmer instance; handle if it does not exist
                try:
                    farmer_profile = owned_by_user.farmer
                except Farmer.DoesNotExist:
                    farmer_profile = None

                first_crate = produce.crates.first()
                cooling_unit = first_crate.cooling_unit

                produce_dict = {
                    "crop": produce.crop.name,
                    "farmer": f"{owned_by_user.first_name} {owned_by_user.last_name}",
                    "farmer_id": farmer_profile.id if farmer_profile else None,
                    "user_id": owned_by_user.id,
                    "checkin_date": produce.checkin.movement.date,
                    "cooling_unit": cooling_unit.name,
                    "cooling_unit_id": cooling_unit.id,
                }

                return produce_dict
        except:
            pass

        return None

    def get_movement_code(self, instance):
        try:
            if instance.event_type == "MARKET_SURVEY":
                movement_code = Checkout.objects.get(
                    id=instance.specific_id
                ).movement.code
                return movement_code
            elif (
                instance.event_type == "TIME_TO_PICKUP"
                or instance.event_type == "FARMER_SURVEY"
            ):
                movement_code = Produce.objects.get(
                    id=instance.specific_id
                ).checkin.movement.code
                return movement_code
            elif instance.event_type == "CHECKIN_EDITED":
                movement_code = Checkin.objects.get(
                    id=instance.specific_id
                ).movement.code
                return movement_code
            elif (
                instance.event_type
                == Notification.NotificationType.LISTING_PRICE_UPDATED
            ):
                movement_code = (
                    Checkin.objects.filter(
                        produces__crates__market_listed_crates__prices__id=instance.specific_id
                    )
                    .first()
                    .movement.code
                )
                return movement_code
        except:
            pass

        return None


class GenericCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenericUserCode
        fields = "__all__"

    def create(self, validated_data):
        code = base64.urlsafe_b64encode(os.urandom(6)).decode()
