from rest_framework import permissions
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import Crate
from base.apps.storage.serializers import CrateSerializer


class CrateViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = Crate
    serializer_class = CrateSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        if self.request.query_params.get(
            "cooling_unit"
        ) and self.request.query_params.get("farmer"):
            return self.model.objects.filter(
                cooling_unit=self.request.query_params.get("cooling_unit"),
                weight__gt=0,
                produce__checkin__owned_by_user__farmer=self.request.query_params.get(
                    "farmer"
                ),
            )
        return self.model.objects.all()
