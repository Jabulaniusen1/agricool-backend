from rest_framework import permissions
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import Produce
from base.apps.user.models import Operator
from base.apps.user.serializers.operator import OperatorSerializer


class OperatorViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    model = Operator
    serializer_class = OperatorSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        if self.request.query_params.get("company"):
            return self.model.objects.filter(
                company_id=self.request.query_params.get("company"),
                user__is_active=True,
            )
        if self.request.query_params.get("user_id"):
            return self.model.objects.filter(
                user_id=self.request.query_params.get("user_id")
            )
        if self.request.query_params.get("produce_id"):
            produce = Produce.objects.get(
                pk=self.request.query_params.get("produce_id")
            )
            return self.model.objects.filter(pk=produce.checkin.movement.operator.id)
        if self.request.query_params.get("movement_id"):
            return self.model.objects.filter(
                operated_movements=self.request.query_params.get("movement_id")
            )
        return self.model.objects.all().filter(user__is_active=True)
