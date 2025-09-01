from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from base.apps.prediction.models import Market, State
from base.apps.prediction.serializers import StateSerializer
from base.apps.storage.models import Crop
from base.apps.user.models import Farmer, Operator, ServiceProvider


class StateViewSet(
    CreateModelMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin
):
    model = State
    serializer_class = StateSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        user = self.request.user
        try:
            country = ServiceProvider.objects.get(user=user).company.country
        except:
            country = Operator.objects.get(user=user).company.country

        return self.model.objects.filter(country__country=country).order_by("name")

    @action(detail=False, methods=["GET"], name="Get ML4 markets")
    def get_parameters_for_prediction(self, request, *args, **kwargs):
        user = self.request.user

        try:
            country = ServiceProvider.objects.get(user=user).company.country
            print(f"Service provider country: {country}!")
        except:
            try:
                country = Operator.objects.get(user=user).company.country
                print(f"operator country: {country}!")

            except:
                country = Farmer.objects.get(user=user).country
                print(f"farmer country: {country}!")

        markets = (
            Market.objects.select_related("state")
            .filter(state__country__country=country, used_for_predictions=True)
            .order_by("state__name", "district", "name")
        )

        marketsDict = {}

        for market in markets:
            if not market.state.name in marketsDict:
                marketsDict[market.state.name] = {}

            if not market.district in marketsDict[market.state.name]:
                marketsDict[market.state.name][market.district] = []

            marketsDict[market.state.name][market.district].append(
                {"id": market.id, "name": market.name}
            )

        # TODO: Beware of performances issues
        available_crops = list(
            Crop.objects.filter(crop_prediction__market__used_for_predictions=True)
            .distinct()
            .values("id", "name")
        )

        return JsonResponse(
            {"available_crops": available_crops, "available_markets": marketsDict}
        )
