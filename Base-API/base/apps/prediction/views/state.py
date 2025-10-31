from django.http import JsonResponse
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
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
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        country = None

        # Try to get country from ServiceProvider or Operator role
        try:
            service_provider = ServiceProvider.objects.get(user=user)
            if service_provider.company and service_provider.company.country:
                country = service_provider.company.country
        except (ServiceProvider.DoesNotExist, AttributeError):
            try:
                operator = Operator.objects.get(user=user)
                if operator.company and operator.company.country:
                    country = operator.company.country
            except (Operator.DoesNotExist, AttributeError):
                pass

        if country is None:
            # User doesn't have required role to access this resource
            return self.model.objects.none()

        return self.model.objects.filter(country__country=country).order_by("name")

    @action(detail=False, methods=["GET"], name="Get ML4 markets")
    def get_parameters_for_prediction(self, request, *args, **kwargs):
        user = self.request.user
        country = None

        # Try to get country from ServiceProvider, Operator, or Farmer role
        try:
            service_provider = ServiceProvider.objects.get(user=user)
            if service_provider.company and service_provider.company.country:
                country = service_provider.company.country
                print(f"Service provider country: {country}!")
        except (ServiceProvider.DoesNotExist, AttributeError):
            try:
                operator = Operator.objects.get(user=user)
                if operator.company and operator.company.country:
                    country = operator.company.country
                    print(f"operator country: {country}!")
            except (Operator.DoesNotExist, AttributeError):
                try:
                    farmer = Farmer.objects.get(user=user)
                    if farmer.country:
                        country = farmer.country
                        print(f"farmer country: {country}!")
                except (Farmer.DoesNotExist, AttributeError):
                    pass

        if country is None:
            # User doesn't have required role to access this resource
            return Response(
                {"error": "Access denied. User must have ServiceProvider, Operator, or Farmer role."},
                status=status.HTTP_403_FORBIDDEN
            )

        markets = (
            Market.objects.select_related("state")
            .filter(state__country__country=country, used_for_predictions=True)
            .order_by("state__name", "district", "name")
        )

        markets_dict = {}

        for market in markets:
            if not market.state.name in markets_dict:
                markets_dict[market.state.name] = {}

            if not market.district in markets_dict[market.state.name]:
                markets_dict[market.state.name][market.district] = []

            markets_dict[market.state.name][market.district].append(
                {"id": market.id, "name": market.name}
            )

        # TODO: Beware of performances issues
        available_crops = list(
            Crop.objects.filter(crop_prediction__market__used_for_predictions=True)
            .distinct()
            .values("id", "name")
        )

        return JsonResponse(
            {"available_crops": available_crops, "available_markets": markets_dict}
        )
