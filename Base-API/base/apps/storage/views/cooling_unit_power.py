from rest_framework import permissions
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import CoolingUnitPower
from base.apps.storage.serializers import CoolingUnitPowerSerializer


class CoolingUnitPowerViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    model = CoolingUnitPower
    serializer_class = CoolingUnitPowerSerializer
    permission_classes = (permissions.AllowAny,)
