from rest_framework import permissions, status
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.operation.models import MarketSurvey
from base.apps.operation.serializers import MarketSurveySerializer

# Constants
OTHER_REASON_VALUE = "other"


class MarketSurveyViewSet(
    RetrieveModelMixin, ListModelMixin, GenericViewSet, CreateModelMixin
):
    model = MarketSurvey
    serializer_class = MarketSurveySerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.all()

    def create(self, request, *args, **kwargs):
        data = request.data
        original_reason_for_loss = data["reason_for_loss"]

        if data["reason_for_loss"] and isinstance(data["reason_for_loss"], list):
            original_reason_for_loss = data["reason_for_loss"]
            data["reason_for_loss"] = OTHER_REASON_VALUE

        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(reason_for_loss=original_reason_for_loss)
        return Response(serializer.data, status=status.HTTP_200_OK)
