from django.http import JsonResponse
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.prediction.models import StateNg
from base.apps.prediction.serializers import StateNgSerializer
from base.apps.user.models import Farmer, Operator, ServiceProvider


class StateViewSetNg(
    CreateModelMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin
):
    model = StateNg
    serializer_class = StateNgSerializer
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

    @action(detail=False, methods=["GET"], name="Get ML4 states for nigeria")
    def get_parameters_for_prediction(self, request, *args, **kwargs):
        user = self.request.user
        country = None
        available_crops = [
            {"id": 37, "name": "Onion"},
            {"id": 44, "name": "Plantain"},
            {"id": 56, "name": "Tomato"},
            {"id": 47, "name": "Irish Potato"},
            {"id": 72, "name": "Sweet Potato"},
        ]

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

        available_states = list(self.model.objects.all().values("id", "name"))

        # TODO Beware of performances issues

        return JsonResponse(
            {"available_crops": available_crops, "available_states": available_states}
        )
