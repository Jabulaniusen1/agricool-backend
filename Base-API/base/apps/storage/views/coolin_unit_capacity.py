from rest_framework import permissions
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import CoolingUnit
from base.apps.storage.serializers import CoolingUnitCapacitySerializer


class CoolingUnitCapacityViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = CoolingUnit
    serializer_class = CoolingUnitCapacitySerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):

        if self.request.query_params.get("cooling_unit"):
            cooling_unit_id = self.request.query_params.get("cooling_unit")
            return self.model.objects.filter(id=cooling_unit_id)
        else:
            return self.model.objects.all()
