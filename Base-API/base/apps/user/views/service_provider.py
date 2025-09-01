from rest_framework import permissions
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.user.models import ServiceProvider
from base.apps.user.serializers.service_provider import ServiceProviderSerializer


class ServiceProviderViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    model = ServiceProvider
    serializer_class = ServiceProviderSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.filter(
            company=self.request.query_params.get("company"), user__is_active=True
        )

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data, status=200)
