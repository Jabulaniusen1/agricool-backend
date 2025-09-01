from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.user.serializers.operator_registration import OperatorRegistrationWithInvitationSerializer


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
