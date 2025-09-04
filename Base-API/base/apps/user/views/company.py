from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.user.models import Company, Operator, ServiceProvider
from base.apps.user.serializers.company import (
    CompanyPublicSerializer,
    CompanySerializer,
)
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
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        """
        Return appropriate serializer based on request context
        """
        # Use public serializer for marketplace requests
        if self.request.query_params.get("marketplace_filter_scoped"):
            return CompanyPublicSerializer

        # Use standard serializer for authenticated users
        return CompanySerializer

    def get_queryset(self):
        queryset = self.model.objects.all()

        # Public marketplace filtering (limited data)
        if self.request.query_params.get("marketplace_filter_scoped"):
            return queryset.filter(
                country__in=MARKETPLACE_OPEN_TO_COUNTRIES,
                flag_opt_out_from_marketplace_filter=False,
            )

        # Authenticated users - filter by user's associated companies
        if self.request.user.is_authenticated:
            user_companies = queryset.filter(
                Q(service_provider_company__user=self.request.user)
                | Q(operator_company__user=self.request.user)
                | Q(worked_with_company__user=self.request.user)
            ).distinct()
            return user_companies

        return queryset.none()

    def update(self, request, *args, **kwargs):
        company = self.get_object()

        serializer = self.get_serializer(
            company, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
