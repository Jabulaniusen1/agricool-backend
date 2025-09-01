from datetime import datetime, timedelta

from rest_framework import permissions
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import CoolingUnitSpecifications
from base.apps.storage.serializers import CoolingUnitSpecificationsSerializer


class CoolingUnitTemperatureViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = CoolingUnitSpecifications
    serializer_class = CoolingUnitSpecificationsSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.filter(
            cooling_unit=self.request.query_params.get("cooling_unit"),
            specification_type="TEMPERATURE",
            # Filter by last 7 days
            datetime_stamp__gte=datetime.now() - timedelta(days=7),
        ).order_by("datetime_stamp")
