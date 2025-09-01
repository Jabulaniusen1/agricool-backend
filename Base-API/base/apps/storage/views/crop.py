from rest_framework import permissions
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import Crop
from base.apps.storage.serializers import CropSerializer
from base.apps.user.models import Country, Farmer, Operator, ServiceProvider


class CropViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = Crop
    serializer_class = CropSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        user = self.request.user

        # For some countries we want to filter crops only specific to them
        try:
            country = ServiceProvider.objects.get(user=user).company.country.name
        except:
            try:
                country = Operator.objects.get(user=user).company.country.name
            except:
                country = Farmer.objects.get(user=user).country

        isFilterCountry = False
        for c in Country.objects.all():
            if c.country.name == country:
                isFilterCountry = True
                break

        if isFilterCountry:
            if "crop" in self.request.data:
                return self.model.objects.filter(
                    crop_type__id=self.request.query_params.get("crop"),
                    countryRelated__country__name=country,
                ).order_by("name")
            else:
                return (
                    self.model.objects.filter(countryRelated__country__name=country)
                    .exclude(name="Other")
                    .order_by("name")
                )

        if "crop" in self.request.data:
            return self.model.objects.filter(
                crop_type__id=self.request.query_params.get("crop")
            ).order_by("name")
        else:
            return self.model.objects.all().order_by("name")
