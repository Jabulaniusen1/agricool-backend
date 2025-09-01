from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from base.apps.prediction.models import StateNg
from base.apps.prediction.serializers import StateNgSerializer
from base.apps.user.models import Farmer, Operator, ServiceProvider


class StateViewSetNg(
    CreateModelMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin
):
    model = StateNg
    serializer_class = StateNgSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        user = self.request.user
        try:
            country = ServiceProvider.objects.get(user=user).company.country
        except:
            country = Operator.objects.get(user=user).company.country

        return self.model.objects.filter(country__country=country).order_by("name")

    @action(detail=False, methods=["GET"], name="Get ML4 states for nigeria")
    def get_parameters_for_prediction(self, request, *args, **kwargs):
        user = self.request.user
        available_crops = [
            {"id": 37, "name": "Onion"},
            {"id": 44, "name": "Plantain"},
            {"id": 56, "name": "Tomato"},
            {"id": 47, "name": "Irish Potato"},
            {"id": 72, "name": "Sweet Potato"},
        ]

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

        available_states = list(self.model.objects.all().values("id", "name"))

        # TODO Beware of performances issues

        return JsonResponse(
            {"available_crops": available_crops, "available_states": available_states}
        )
