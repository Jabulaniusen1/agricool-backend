from rest_framework import permissions
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.operation.models import MarketSurvey
from base.apps.operation.serializers import MarketSurveySerializer


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
        temp = data["reason_for_loss"]

        if data["reason_for_loss"] and isinstance(data["reason_for_loss"], list):
            temp = data["reason_for_loss"]
            data["reason_for_loss"] = "other"

        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save(reason_for_loss=temp)
        return Response(serializer.data, status=200)
