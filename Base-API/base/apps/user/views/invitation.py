from datetime import datetime

from django.utils import timezone, translation
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.services.mail import invitation_mail_service
from base.apps.user.models import InvitationUser, User
from base.apps.user.serializers.invitation import InvitationUserSerializer
from base.celery import app
from base.settings import (
    FRONTEND_URL,
    INVITATION_OPERATOR_URL,
    INVITATION_SERVICE_PROVIDER_URL,
)
from base.utils.recaptcha import validate_recaptcha_field


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
        # Validate reCAPTCHA for service provider invitations  
        validate_recaptcha_field(request.data)
        
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
        print(
            "base.apps.user.tasks.sms.send_sms_invite_service_provider_with_code",
            [request.user.id, serializer.data["phone"], link],
        )
        app.send_task(
            "base.apps.user.tasks.sms.send_sms_invite_service_provider_with_code",
            [request.user.id, serializer.data["phone"], link],
        )

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
        # Validate reCAPTCHA for operator invitations
        validate_recaptcha_field(request.data)
        
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
        with translation.override(request.user.language or "en"):
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
        print(
            "base.apps.user.tasks.sms.send_sms_invite_operator_with_code",
            [request.user.id, serializer.data["phone"], link],
        )
        app.send_task(
            "base.apps.user.tasks.sms.send_sms_invite_operator_with_code",
            [request.user.id, serializer.data["phone"], link],
        )

        return Response({}, status=200)
