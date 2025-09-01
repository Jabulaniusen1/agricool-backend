from datetime import datetime, timedelta

from rest_framework import permissions
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import CoolingUnitSpecifications
from base.apps.storage.serializers import CoolingUnitSpecificationsSerializer


class CoolingUnitSpecificationsViewSet(
    RetrieveModelMixin, ListModelMixin, GenericViewSet, CreateModelMixin
):
    model = CoolingUnitSpecifications
    serializer_class = CoolingUnitSpecificationsSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.filter(
            cooling_unit=self.request.query_params.get("cooling_unit"),
            datetime_stamp__gte=datetime.now() - timedelta(days=7),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
