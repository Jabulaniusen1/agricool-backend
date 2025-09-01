from rest_framework import permissions
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.user.models import Company
from base.apps.user.serializers.company import CompanySerializer
from base.settings import MARKETPLACE_OPEN_TO_COUNTRIES


class CompanyViewSet(
    CreateModelMixin,
    GenericViewSet,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
):
    model = Company
    serializer_class = CompanySerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        queryset = self.model.objects.all()

        if self.request.query_params.get("marketplace_filter_scoped", None):
            return queryset.filter(
                country__in=MARKETPLACE_OPEN_TO_COUNTRIES,
                flag_opt_out_from_marketplace_filter=False,
            )

        return queryset

    def update(self, request, *args, **kwargs):
        company = self.get_object()

        serializer = self.serializer_class(
            company, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data, status=200)
