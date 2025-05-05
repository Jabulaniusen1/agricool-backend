from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone, translation
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.mixins import (CreateModelMixin, ListModelMixin,
                                   RetrieveModelMixin, UpdateModelMixin)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_400_BAD_REQUEST,
                                   HTTP_403_FORBIDDEN)
from rest_framework.viewsets import GenericViewSet, ViewSet
from rest_framework_simplejwt.views import TokenObtainPairView

from base.apps.storage.models.location import Location
from base.apps.storage.services.mail import invitation_mail_service
from base.celery import app
from base.settings import (AUTH_PASSWORD_URL, ENVIRONMENT, FRONTEND_URL,
                           INVITATION_OPERATOR_URL,
                           INVITATION_SERVICE_PROVIDER_URL,
                           MARKETPLACE_OPEN_TO_COUNTRIES)

from ..storage.models import CoolingUnit, Location, Produce
from .models import (BankAccount, Company, Farmer, FarmerSurvey,
                     FarmerSurveyCommodity, GenericUserCode, InvitationUser,
                     Notification, Operator, ServiceProvider, User)
from .serializers import (CompanySerializer, FarmerLoginSerializer,
                          FarmerSerializer, FarmerSurveySerializer,
                          GenericCodeSerializer, InvitationUserSerializer,
                          NotificationSerializer, OperatorLoginSerializer,
                          OperatorRegistrationWithInvitationSerializer,
                          OperatorSerializer, ServiceProviderLoginSerializer,
                          ServiceProviderRegistrationSerializer,
                          ServiceProviderRegistrationWithInvitationSerializer,
                          ServiceProviderSerializer, UserSerializer)


class UserViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    model = User
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)
    permissions_get = ["user.view_all_users"]

    def get_queryset(self):
        return self.model.objects.all()

    def update(self, request, *args, **kwargs):
        instance = get_object_or_404(User, pk=self.kwargs.get("pk", None))

        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
            instance=instance,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    def delete(self, request, *args, **kwargs):
        user = request.user
        user_id = self.kwargs.get("pk")

        if not user_id:
            return Response({"error": "User ID is required"}, status=HTTP_400_BAD_REQUEST)

        user_to_delete = get_object_or_404(User, id=user_id)

        if user.id != user_to_delete.id:
            return Response({"error": "You can only delete your own account"}, status=HTTP_403_FORBIDDEN)

        try:
            service_provider = ServiceProvider.objects.filter(user=user_to_delete).first()
            if service_provider:
                message = (
                    f"The Registered Employee with the id {user_to_delete.id} of the company {service_provider.company.name} has deleted their account.\n\n"
                    f"Name: {user_to_delete.first_name} {user_to_delete.last_name}\n"
                    f"Phone: {user_to_delete.phone} Email: {user_to_delete.email}\n\n"
                    f"In this company, there are {service_provider.company.service_provider_company.filter(user__is_active=True).count() - 1} Registered employees left."
                )
                if service_provider.company.service_provider_company.filter(user__is_active=True).count() - 1 == 0:
                    company = service_provider.company
                    company.name = f"Deleted company {company.id}"
                    company.logo.delete()
                    company.save()
                    CoolingUnit.objects.filter(location__company_id=company.id, deleted=False).update(name="Deleted cooling unit", deleted=True)
                    Location.objects.filter(company__id=company.id, deleted=False).update(
                        deleted=True, name=None, state="", city="", street="", street_number=None, zip_code="", point=[0, 0]
                    )
                    Operator.objects.filter(company__id=company.id, user__is_active=True).update(
                        user__is_active=False, user__first_name="User", user__last_name="Disable", user__phone=None, user__email=None
                    )
            
            operator = Operator.objects.filter(user=user_to_delete).first()
            if operator:
                remaining_operators = Operator.objects.filter(company__id=operator.company.id, user__is_active=True)
                message = (
                    f"The operator with the id {user_to_delete.id} of the company {operator.company.name} has deleted their account.\n\n"
                    f"Name: {user_to_delete.first_name} {user_to_delete.last_name}\n"
                    f"Phone: {user_to_delete.phone}\n\n"
                    f"In this company, there are {remaining_operators.count() - 1} Operators left."
                )
                CoolingUnit.objects.filter(operators=user_to_delete).update(operators=None)

            # Avoid send the mails on dev
            if ENVIRONMENT != "development":
                try:
                    send_mail("User deletion", message, settings.DEFAULT_FROM_EMAIL, ["app@yourvcca.org"])
                except Exception as e:
                    print(f"Error sending the mail: {e}")

            user_to_delete.is_active = False
            user_to_delete.first_name = "User"
            user_to_delete.last_name = "Disable"
            user_to_delete.phone = None
            user_to_delete.email = None
            user_to_delete.save()
            return Response({"success": "Successfully deleted user"}, status=HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"error": "Error in deleting user"}, status=HTTP_400_BAD_REQUEST)
        
    
    @action(detail=True, methods=["delete"], url_path="operator-proxy-delete")
    def operator_proxy_delete(self, request, pk=None, **kwargs):
        """
        Allows an authenticated operator to deactivate a farmer account under specific conditions.

        This endpoint is intended as a proxy delete mechanism for operators to manage farmer accounts 
        when the user cannot delete their account themselves (e.g., no smartphone access or app usage).

        Requirements:
        - The requesting user must have the operator role.
        - The target user must have the farmer role.
        - Both users must belong to the same company.
        - The target user must not be a smartphone user (user_code is None and smartphone is False).

        Deactivation includes:
        - Disabling the user's account (is_active = False).
        - Anonymizing personal information (name, phone, email).
        - Removing the user from any assigned cooling units.

        Returns:
        - 200 OK on successful deletion.
        - 400/403 errors for failed validations or conditions.
        """
     
        operator_user = request.user
        target_user = get_object_or_404(User, id=pk)

        # Check operator role
        operator = Operator.objects.filter(user=operator_user).first()
        if not operator:
            return Response({"error": "Only users with the operator role can perform this action"}, status=HTTP_403_FORBIDDEN)

        # Validate if target is farmer
        farmer = Farmer.objects.filter(user=target_user).first()
  
        if not farmer:
            return Response({"error": "Cannot delete users who don't have the farmer role"}, status=HTTP_400_BAD_REQUEST)

        # Same company check
        if not farmer.companies.filter(id=operator.company_id).exists():
            return Response({"error": "Cannot delete a user that does not belong to your company"}, status=HTTP_403_FORBIDDEN)

        # Smartphone check
        if farmer.user_code is not None or farmer.smartphone:
            return Response({"error": "Cannot delete users with smartphone"}, status=HTTP_400_BAD_REQUEST)

        try:
            target_user.is_active = False
            target_user.first_name = "User"
            target_user.last_name = "Disable"
            target_user.phone = None
            target_user.email = None
            target_user.save()

            return Response({"success": "User deleted by operator"}, status=HTTP_200_OK)
        except Exception as e:
            print(f"Error in operator_proxy_delete: {e}")
            return Response({"error": "Something went wrong"}, status=HTTP_400_BAD_REQUEST)

class CompanyViewSet(
    CreateModelMixin,
    GenericViewSet,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
):
    model = Company
    serializer_class = CompanySerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        queryset = self.model.objects.all()

        if self.request.query_params.get('marketplace_filter_scoped', None):
            return queryset.filter(
                country__in=MARKETPLACE_OPEN_TO_COUNTRIES,
                flag_opt_out_from_marketplace_filter=False,
            )

        return queryset

    def update(self, request, *args, **kwargs):
        company = self.get_object()

        serializer = self.serializer_class(
            company, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data,  status=200)


class ServiceProviderViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    model = ServiceProvider
    serializer_class = ServiceProviderSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.filter(
            company=self.request.query_params.get("company"), user__is_active=True
        )

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data, status=200)


class OperatorViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    model = Operator
    serializer_class = OperatorSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        if self.request.query_params.get("company"):
            return self.model.objects.filter(
                company_id=self.request.query_params.get("company"), user__is_active=True
            )
        if self.request.query_params.get("user_id"):
            return self.model.objects.filter(
                user_id=self.request.query_params.get("user_id")
            )
        if self.request.query_params.get("produce_id"):
            produce = Produce.objects.get(
                pk=self.request.query_params.get("produce_id")
            )
            return self.model.objects.filter(pk=produce.checkin.movement.operator.id)
        if self.request.query_params.get("movement_id"):
            return self.model.objects.filter(
                operated_movements=self.request.query_params.get("movement_id")
            )
        return self.model.objects.all().filter(user__is_active=True)


class FarmerViewSet(
    GenericViewSet, ListModelMixin, UpdateModelMixin, RetrieveModelMixin
):
    model = Farmer
    serializer_class = FarmerSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        if self.request.query_params.get("user_id"):
            return self.model.objects.filter(
                Q(user__id=self.request.query_params.get("user_id"))
            )

        if self.request.query_params.get("operator"):
            operator_user_id = self.request.query_params.get("operator")

            return self.model.objects.filter(
                Q(created_by__company__operator_company__user_id=operator_user_id)
                | Q(companies__operator_company__user_id=operator_user_id),
                user__is_active=True,
            ).distinct()

        if self.request.query_params.get("user_code"):
            user_code = self.request.query_params.get("user_code")
            return self.model.objects.filter(user_code=user_code, user__is_active=True)

        return self.model.objects.all()

    def create(self, request, *args, **kwargs):
        if not request.data["createUser"] and (
            not request.user or not request.user.is_authenticated
        ):
            raise PermissionDenied()
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data, status=200)

    def update(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk", None)
        instance = get_object_or_404(Farmer, id=pk)
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
            instance=instance,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_serializer(self, *args, **kwargs):
        kwargs['context'] = self.get_serializer_context()
        return super().get_serializer(*args, **kwargs)


class InviteServiceProviderViewSet(
    CreateModelMixin, GenericViewSet, RetrieveModelMixin, ListModelMixin
):
    lookup_field = "code"
    model = InvitationUser
    serializer_class = InvitationUserSerializer
    permission_classes = (permissions.IsAuthenticated,)
    permissions = [
        "user.add_invitation_serviceprovider",
    ]

    def get_queryset(self):
        if self.request.query_params.get("company"):
            return self.model.objects.filter(
                expiration_date__gt=datetime.now(),
                user_type=1,
                sender__service_provider__company=self.request.query_params.get(
                    "company"
                ),
            )

        # invites are only valid if they are not expired
        return self.model.objects.filter(
            expiration_date__gt=timezone.now(), user_type=1
        )

    def get_object(self):
        invitation = (
            self.get_queryset().filter(code=self.kwargs["code"]).order_by("id").last()
        )

        if not invitation:
            raise NotFound

        return invitation

    def create(self, request, *args, **kwargs):
        if (
            not request.user
            or not request.user.is_authenticated
            or not request.user.has_perms(self.permissions)
        ):
            raise PermissionDenied()

        invitation_data = request.data
        invitation_data["user_type"] = 1
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save()

        # construct link url
        link = INVITATION_SERVICE_PROVIDER_URL.format(
            base_url=FRONTEND_URL,
            code=serializer.data["code"],
            phone_number=serializer.data["phone"],
        )

        try:
            user = User.objects.get(id=invitation_data["user_id"])
            recipient_list = [user.email]
            invitation_mail_service(
                "Registered Employee",
                link,
                serializer.data["phone"],
                recipient_list,
                serializer.data["expiration_date"],
            )
        except:
            print("Error sending the mail")


        # enqueue sms to be sent
        print("base.apps.user.tasks.sms.send_sms_invite_service_provider_with_code", [request.user.id, serializer.data["phone"], link])
        app.send_task("base.apps.user.tasks.sms.send_sms_invite_service_provider_with_code", [request.user.id, serializer.data["phone"], link])

        return Response({}, status=200)


class InviteOperatorViewSet(
    CreateModelMixin, RetrieveModelMixin, GenericViewSet, ListModelMixin
):
    lookup_field = "code"
    model = InvitationUser
    serializer_class = InvitationUserSerializer
    permission_classes = (permissions.IsAuthenticated,)
    permissions = [
        "user.add_invitation_operator",
    ]

    def get_queryset(self):
        if self.request.query_params.get("company"):
            return self.model.objects.filter(
                expiration_date__gt=datetime.now(),
                user_type=2,
                sender__service_provider__company=self.request.query_params.get(
                    "company"
                ),
            )
        # invites are only valid if they are not expired
        return self.model.objects.filter(
            expiration_date__gt=datetime.now(), user_type=2
        )

    def get_object(self):
        invitation = (
            self.get_queryset().filter(code=self.kwargs["code"]).order_by("id").last()
        )
        if not invitation:
            raise NotFound
        return invitation

    def create(self, request, *args, **kwargs):
        if (
            not request.user
            or not request.user.is_authenticated
            or not request.user.has_perms(self.permissions)
        ):
            raise PermissionDenied()
        invitation_data = request.data
        invitation_data["user_type"] = 2

        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save()

        # construct link url
        link = INVITATION_OPERATOR_URL.format(
            base_url=FRONTEND_URL,
            code=serializer.data["code"],
            phone_number=serializer.data["phone"],
        )

        # construct message
        with translation.override(request.user.language or 'en'):
            message = translation.gettext("sms_invite_operator_with_code").format(
                link=link
            )

        try:
            user = User.objects.get(id=invitation_data["user_id"])
            recipient_list = [user.email]
            invitation_mail_service(
                "Operator",
                link,
                serializer.data["phone"],
                recipient_list,
                serializer.data["expiration_date"],
            )
        except:
            print("Error sending the mail")

        # enqueue sms to be sent
        print("base.apps.user.tasks.sms.send_sms_invite_operator_with_code", [request.user.id, serializer.data["phone"], link])
        app.send_task("base.apps.user.tasks.sms.send_sms_invite_operator_with_code", [request.user.id, serializer.data["phone"], link])

        return Response({}, status=200)

class ServiceProviderRegistrationViewSet(GenericViewSet):
    serializer_class = ServiceProviderRegistrationSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):

        # TOD : have cleaner way to do this
        if "bank_account" in request.data['company']:
            bank_instance_created = BankAccount.objects.create(
                bank_name=request.data['company']["bank_account"]["bank_name"],
                account_name=request.data['company']["bank_account"]["account_name"],
                account_number=request.data['company']["bank_account"]["account_number"],
            )
            request.data['company']["bank_account"] = bank_instance_created.id

        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data, status=200)


class ServiceProviderRegistrationWithInvitationViewSet(GenericViewSet):
    serializer_class = ServiceProviderRegistrationWithInvitationSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data, status=200)


class OperatorRegistrationWithInvitationViewSet(GenericViewSet):
    serializer_class = OperatorRegistrationWithInvitationSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data, status=200)


class LoginViewSet(TokenObtainPairView):
    serializer_class = FarmerLoginSerializer

    def get_serializer_class(self):
        if "user_type" in self.request.data:
            user_type = self.request.data.get("user_type", None)
            if user_type == "sp":
                return ServiceProviderLoginSerializer
            if user_type == "op":
                return OperatorLoginSerializer
            if user_type == "f":
                return FarmerLoginSerializer
        return None


class FarmerSurveyViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    model = FarmerSurvey
    serializer_class = FarmerSurveySerializer
    permission_classes = (permissions.AllowAny,)


    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            raise AuthenticationFailed("Authentication credentials were not provided.")

        user_id = self.request.query_params.get("farmer_id")

        try:
            farmer = Farmer.objects.get(user__id=user_id)
        except ObjectDoesNotExist:
            farmer = None

        if farmer and farmer.user == user:
            return self.model.objects.filter(farmer=farmer)

        if Operator.objects.filter(user=user).exists():
            operator = Operator.objects.get(user=user)
            company_id = operator.company_id
            
            if farmer and farmer.companies.filter(id=company_id).exists():
                return self.model.objects.filter(farmer=farmer)

        raise AuthenticationFailed("You are not authorized to view this survey.")

    def create(self, request, *args, **kwargs):

        serializer = self.serializer_class(
            data=request.data,
            context={"request": request, "commodities": request.data["commodities"]},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data, status=200)

    def update(self, request, *args, **kwargs):
        data = request.data
        farmer = Farmer.objects.get(id=request.data["farmer"])
        experience = True if data["experience"] == "yes" else False
        instance = FarmerSurvey.objects.filter(farmer=farmer).first()
        if instance:
            FarmerSurvey.objects.filter(farmer=farmer).update(
                user_type=data["user_type"],
                experience=experience,
                experience_duration=data["experience_duration"],
                date_last_modified=datetime.now().astimezone(),
            )
        else:
            instance = FarmerSurvey.objects.create(
                farmer=farmer,
                user_type=data["user_type"],
                experience=experience,
                experience_duration=data["experience_duration"],
                date_filled_in=datetime.now().astimezone(),
                date_last_modified=datetime.now().astimezone(),
            )

        existing_commodities = list(
            FarmerSurveyCommodity.objects.filter(farmer_survey=instance.id).values(
                "crop_id", "date_filled_in"
            )
        )
        FarmerSurveyCommodity.objects.filter(farmer_survey=instance.id).delete()
        for crop_item in data["commodities"]:
            if crop_item["crop_id"] != "":
                old_commodity_date = next(
                    (
                        co["date_filled_in"]
                        for co in existing_commodities
                        if co["crop_id"] == crop_item["crop_id"]
                    ),
                    False,
                )
                FarmerSurveyCommodity.objects.create(
                    farmer_survey_id=instance.id,
                    crop_id=crop_item["crop_id"],
                    average_price=crop_item["average_price"],
                    unit=crop_item["unit"],
                    kg_in_unit=crop_item["kg_in_unit"],
                    reason_for_loss=crop_item["reason_for_loss"],
                    quantity_total=crop_item["quantity_total"],
                    quantity_self_consumed=crop_item["quantity_self_consumed"],
                    quantity_sold=crop_item["quantity_sold"],
                    quantity_below_market_price=crop_item[
                        "quantity_below_market_price"
                    ],
                    average_season_in_months=crop_item["average_season_in_months"],
                    currency=crop_item["currency"],
                    date_filled_in=(
                        old_commodity_date
                        if old_commodity_date
                        else datetime.now().astimezone()
                    ),
                    date_last_modified=datetime.now().astimezone(),
                )

        return Response(
            FarmerSurvey.objects.filter(farmer__id=request.data["farmer"]).values(),
            status=200,
        )


class ResetPasswordViewSet(GenericViewSet):
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        if "phoneNumber" in request.data:
            # this is for requesting the reset
            phone_number = request.data["phoneNumber"]
            user = None

            try:
                user = User.objects.get(phone=phone_number)
            except:
                # This endpoint should not disclose whether the user exists or not
                return Response({}, status=200)

            try:
                existing_code = GenericUserCode.objects.get(user=user)
                existing_code.delete()
                existing_code = None
            except:
                existing_code = None

            # to avoid bot spamming, we allow request reset only every 2 hours
            if existing_code:
                if datetime.now().astimezone() < (
                    existing_code.expiration_date.astimezone() - timedelta(hours=4)
                ):
                    return Response(
                        {"error": "Can only request every 2 hours.", "error-code": "2"},
                        status=400,
                    )

            # we replace reset requests for the same number
            if existing_code:
                GenericUserCode.objects.filter(user=user).delete()

            time = datetime.now().astimezone() + timedelta(hours=6)
            code = GenericUserCode.generate_code(phone=phone_number)
            # code = base64.urlsafe_b64encode(os.urandom(6)).decode()
            GenericUserCode.objects.create(
                type="RESET", user=user, code=code, expiration_date=time
            )

            # construct link url
            link = AUTH_PASSWORD_URL.format(
                base_url=FRONTEND_URL,
                code=code,
                phone_number=user.phone,
            )

            if user.email:
                subject = "Password Reset"
                email_from = settings.DEFAULT_FROM_EMAIL
                recipient_list = [user.email]

                # construct message
                with translation.override(user.language or 'en'):
                    message = translation.gettext("sms_auth_reset_password").format(
                        link=link
                    )

                send_mail(subject, message, email_from, recipient_list)

            app.send_task("base.apps.user.tasks.sms.send_sms_auth_reset_password", [user.id, phone_number, link])

            return Response({}, status=200)

        else:
            # here we actually reset the password
            phone_number = request.data["phone"]
            password = request.data["password"]
            code = request.data["code"]

            try:
                user = User.objects.get(phone=phone_number)
            except:
                return Response(
                    {"error-message": "User does not exist", "error-code": "1"},
                    status=400,
                )

            try:
                generic_code_object = GenericUserCode.objects.get(code=code)
            except:
                return Response(
                    {"error-message": "Reset not requested", "error-code": "2"},
                    status=400,
                )

            expired = generic_code_object.expiration_date < datetime.now().astimezone()
            if expired:
                return Response(
                    {"error-message": "Reset Code Expired", "error-code": "3"},
                    status=400,
                )

            new_number = generic_code_object.user.phone

            u = User.objects.get(phone=new_number)
            u.set_password(password)
            u.save()

            return Response({"message": "success"}, status=200)


class GenericCodeViewSet(GenericViewSet):
    serializer_class = GenericCodeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data, status=200)


class NotificationViewSet(
    GenericViewSet,
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
):
    model = Notification
    serializer_class = NotificationSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")

        authenticated_user = self.request.user

        if user_id is None or user_id != str(authenticated_user.id):
            raise AuthenticationFailed("You are not authorized to view these notifications.")

        week_delta = datetime.now().astimezone() - timedelta(days=7)
        return Notification.objects.filter(
            Q(user=authenticated_user) & (Q(seen=False) | Q(date__gt=week_delta))
        ).order_by("-date")

    def create(self, request, *args, **kwargs):
        user_id = self.request.user.id
        hours_delta = datetime.now().astimezone() - timedelta(hours=6)
        lastSensorNotification = (
            Notification.objects.filter(
                Q(user=user_id),
                Q(date__gt=hours_delta),
                event_type=Notification.NotificationType.SENSOR_ERROR,
            ).last()
            if user_id
            else None
        )
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            if user_id is not None and lastSensorNotification is None:
                serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    def update(self, request, *args, **kwargs):
        instance = get_object_or_404(Notification, pk=self.kwargs.get("pk", None))
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
            instance=instance,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)


class DevelopmentViewSet(ViewSet):
    permission_classes = (AllowAny,)
    lookup_field = 'id'

    @action(methods=['GET'], url_path='test', detail=False)
    def test(self, request):
        return Response({ "message": "Hello World!" }, status=HTTP_200_OK)


    @action(methods=['GET'], url_path='last-sent-sms', detail=False)
    def last_sent_sms(self, request):
        phoneNumber = request.query_params.get('phoneNumber')

        if not phoneNumber:
            return Response({"sent": None}, status=HTTP_400_BAD_REQUEST)

        result = app.send_task("base.apps.user.tasks.sms.get_last_sent_sms", args=[phoneNumber])
        lastSmsSent = result.get(timeout=10)  # Wait up to 10 seconds for the result
        if not lastSmsSent:
            return Response({"sent": None}, status=HTTP_200_OK)

        return Response({"last_sms_sent": lastSmsSent}, status=HTTP_200_OK)
