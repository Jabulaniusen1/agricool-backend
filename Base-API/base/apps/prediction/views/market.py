from rest_framework import permissions
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.prediction.models import Market
from base.apps.prediction.serializers import MarketSerializer


class MarketViewSet(
    CreateModelMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin
):
    model = Market
    serializer_class = MarketSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.filter(
            state__country=self.request.query_params.get("country")
        ).order_by("name")

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context={
                "country": request.data["country"],
                "state": request.data["state_name"],
            },
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)

        return Response(serializer.errors, status=400)
