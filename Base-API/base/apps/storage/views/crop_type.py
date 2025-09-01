from rest_framework import permissions
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import CropType
from base.apps.storage.serializers import CropTypeSerializer


class CropTypeViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = CropType
    serializer_class = CropTypeSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.order_by("name")
