from rest_framework import permissions
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import Crate
from base.apps.storage.serializers import CrateSerializer

# Default values
DEFAULT_WEIGHT_THRESHOLD = 0


class CrateViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = Crate
    serializer_class = CrateSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        base_queryset = self.model.objects.select_related(
            'produce',
            'cooling_unit', 
            'produce__checkin',
            'produce__checkin__owned_by_user',
            'produce__checkin__owned_by_user__farmer',
            'produce__crop'
        )
        
        if self.request.query_params.get(
            "cooling_unit"
        ) and self.request.query_params.get("farmer"):
            return base_queryset.filter(
                cooling_unit=self.request.query_params.get("cooling_unit"),
                weight__gt=DEFAULT_WEIGHT_THRESHOLD,
                produce__checkin__owned_by_user__farmer=self.request.query_params.get(
                    "farmer"
                ),
            )
        return base_queryset
