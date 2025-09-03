from rest_framework import permissions
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import Produce
from base.apps.user.models import Operator
from base.apps.user.serializers.operator import OperatorSerializer

# Request parameter constants
COMPANY_PARAM = "company"
USER_ID_PARAM = "user_id"
PRODUCE_ID_PARAM = "produce_id"
MOVEMENT_ID_PARAM = "movement_id"

# Default values
DEFAULT_IS_ACTIVE = True


class OperatorViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    model = Operator
    serializer_class = OperatorSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        if self.request.query_params.get(COMPANY_PARAM):
            return self.model.objects.filter(
                company_id=self.request.query_params.get(COMPANY_PARAM),
                user__is_active=DEFAULT_IS_ACTIVE,
            )
        if self.request.query_params.get(USER_ID_PARAM):
            return self.model.objects.filter(
                user_id=self.request.query_params.get(USER_ID_PARAM)
            )
        if self.request.query_params.get(PRODUCE_ID_PARAM):
            try:
                produce = Produce.objects.get(
                    pk=self.request.query_params.get(PRODUCE_ID_PARAM)
                )
            except Produce.DoesNotExist:
                return Operator.objects.none()
            return self.model.objects.filter(pk=produce.checkin.movement.operator.id)
        if self.request.query_params.get(MOVEMENT_ID_PARAM):
            return self.model.objects.filter(
                operated_movements=self.request.query_params.get(MOVEMENT_ID_PARAM)
            )
        return self.model.objects.all().filter(user__is_active=DEFAULT_IS_ACTIVE)
