from django.db.models import Q
from rest_framework import permissions
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import CoolingUnitCrop
from base.apps.storage.serializers import CoolingUnitCropSerializer
from base.apps.user.models import Operator


class CoolingUnitCropViewSet(
    RetrieveModelMixin,
    UpdateModelMixin,
    ListModelMixin,
    GenericViewSet,
    CreateModelMixin,
):
    model = CoolingUnitCrop
    serializer_class = CoolingUnitCropSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        company = Operator.objects.get(user=self.request.user).company
        return self.model.objects.filter(
            Q(cooling_unit__id=self.request.query_params.get("cooling_unit_id"))
            & Q(crop__crop_type__id=self.request.query_params.get("crop"))
            & Q(active=True)
            & (Q(crop__in=company.crop.all()) | Q(crop__name="Other"))
        ).order_by("crop__name")
