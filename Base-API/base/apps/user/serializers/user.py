import uuid

from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from base.apps.storage.models import CoolingUnit
from base.apps.user.models import Operator, ServiceProvider, User

# Field constants
MIN_PASSWORD_LENGTH = 8
UUID_USERNAME_LENGTH = 30

# Request field names
COOLING_UNITS_FIELD = "cooling_units"

# Response field names
PHONE_FIELD = "phone"
EMAIL_FIELD = "email"

# Default values
DEFAULT_NONE = None


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(min_length=MIN_PASSWORD_LENGTH, write_only=True)

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

        # Handle phone and email visibility (keep existing logic)
        self._handle_contact_info_visibility(data, instance, user)
        
        # Handle PII fields visibility (new logic)
        self._handle_pii_visibility(data, instance, user)

        return data

    def _handle_contact_info_visibility(self, data, instance, user):
        """Handle phone and email visibility based on existing logic"""
        if not instance.is_phone_public and not instance.is_email_public:
            # Check if it's the user's own profile
            if instance == user:
                return

            # Skip visibility logic for anonymous users (e.g., during signup)
            if not user.is_authenticated:
                return

            # Check Operator, Employee, or Farmer logic
            operator = Operator.objects.filter(user=user).first()
            employee = ServiceProvider.objects.filter(user=user).first()
            farmer = getattr(user, "farmer", None)
            
            company_id = None
            if operator:
                company_id = operator.company_id
            elif employee:
                company_id = employee.company_id
            elif farmer:
                # For farmers, get any company they belong to (take first one)
                company_id = farmer.companies.first().id if farmer.companies.exists() else None

            if company_id:
                # Check if the target user belongs to the same company
                target_farmer = getattr(instance, "farmer", None)
                target_operator = Operator.objects.filter(user=instance).first()
                
                has_company_access = False
                if target_farmer:
                    has_company_access = target_farmer.companies.filter(id=company_id).exists()
                elif target_operator:
                    has_company_access = target_operator.company_id == company_id
                
                if not has_company_access:
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

    def _handle_pii_visibility(self, data, instance, user):
        """Handle PII fields visibility (gender, language, last_login)"""
        # Always allow users to see their own PII
        if instance == user:
            return

        # last_login is only visible to the user themselves
        data.pop("last_login", None)

        # Check if the viewing user can see gender and language
        if not self._can_view_pii(instance, user):
            data.pop("gender", None)
            data.pop("language", None)

    def _can_view_pii(self, instance, viewing_user):
        """
        Determine if viewing_user can see PII of instance based on company relationships
        Rules:
        - Farmer: Visible to operators/employees from same company
        - Employee (ServiceProvider): Only visible to themselves (already handled above)
        - Operator: Visible to employees from same company
        """
        # Anonymous users cannot view PII
        if not viewing_user or viewing_user.is_anonymous:
            return False
            
        # Get the roles of the viewing user
        viewing_operator = Operator.objects.filter(user=viewing_user).first()
        viewing_employee = ServiceProvider.objects.filter(user=viewing_user).first()

        if not (viewing_operator or viewing_employee):
            # Viewing user has no operator/employee role
            return False

        viewing_company_id = (
            viewing_operator.company_id if viewing_operator
            else viewing_employee.company_id if viewing_employee
            else None
        )

        if not viewing_company_id:
            return False

        # Check the target instance's role
        target_farmer = getattr(instance, "farmer", None)
        target_operator = Operator.objects.filter(user=instance).first()

        # If target is a farmer, operators/employees from same company can see PII
        if target_farmer:
            return target_farmer.companies.filter(id=viewing_company_id).exists()

        # If target is an operator, only employees from same company can see PII
        if target_operator and viewing_employee:
            return target_operator.company_id == viewing_company_id

        # If target is an employee, no one else can see their PII (handled above)
        return False

    @atomic
    def create(self, validated_data):
        password = validated_data.pop("password", None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.username = uuid.uuid4().hex[:UUID_USERNAME_LENGTH]
        instance.save()
        return instance

    def update(self, instance, validated_data):
        # get the cooling units sent with the user
        cooling_units = self.context["request"].data[COOLING_UNITS_FIELD]

        if cooling_units != DEFAULT_NONE:
            # get the cooling units the operator is assigned to already
            operator_cooling_units = CoolingUnit.objects.filter(
                operators=instance
            ).values("id")

            # if one of the cooling unit sent with the request is not already assigned to the op, assign op to it
            for cu in cooling_units:
                try:
                    cooling_unit = CoolingUnit.objects.get(id=cu)
                    if instance not in cooling_unit.operators.all():
                        cooling_unit.operators.add(instance.id)
                except CoolingUnit.DoesNotExist:
                    continue

            # if a cooling unit assigned to the op is not part of the cooling units sent in the request, remove op from it
            for op_cu in operator_cooling_units:
                if op_cu["id"] not in cooling_units:
                    try:
                        CoolingUnit.objects.get(id=op_cu["id"]).operators.remove(
                            instance.id
                        )
                    except CoolingUnit.DoesNotExist:
                        continue

        return super().update(instance, validated_data)


class PublicUserSerializer(UserSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["phone"] = str(instance.phone) if instance.phone else None
        data["email"] = str(instance.email) if instance.email else None
        return data
