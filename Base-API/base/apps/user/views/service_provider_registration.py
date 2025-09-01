from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.user.models import BankAccount
from base.apps.user.serializers.service_provider_registration import (
    ServiceProviderRegistrationSerializer,
    ServiceProviderRegistrationWithInvitationSerializer,
)


class ServiceProviderRegistrationViewSet(GenericViewSet):
    serializer_class = ServiceProviderRegistrationSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):

        # TODO : have cleaner way to do this
        if "bank_account" in request.data["company"]:
            bank_instance_created = BankAccount.objects.create(
                bank_name=request.data["company"]["bank_account"]["bank_name"],
                account_name=request.data["company"]["bank_account"]["account_name"],
                account_number=request.data["company"]["bank_account"][
                    "account_number"
                ],
            )
            request.data["company"]["bank_account"] = bank_instance_created.id

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
